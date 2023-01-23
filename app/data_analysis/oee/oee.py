from datetime import datetime, timedelta, time, date

from flask import current_app

from app.data_analysis import OEECalculationException
from app.data_analysis.helpers import get_daily_values_dict
from app.data_analysis.oee.availability import get_machine_availability
from app.data_analysis.oee.models import DailyOEE
from app.data_analysis.oee.performance import get_machine_performance
from app.data_analysis.oee.quality import get_machine_quality
from app.default.models import MachineGroup, Machine
from app.extensions import db


def calculate_machine_oee(machine, time_start: datetime, time_end: datetime):
    """ Takes a machine id and two times, and returns the machine's OEE figure as a percent"""

    if time_end > datetime.now():
        current_app.logger.warn(f"Machine oee requested for future date {time_end.strftime(('%Y-%m-%d'))}")
        raise OEECalculationException("Machine OEE requested for future date")

    availability = get_machine_availability(machine, time_start, time_end)
    performance = get_machine_performance(machine, time_start, time_end)
    quality = get_machine_quality(machine, time_start, time_end)
    oee = availability * performance * quality
    return oee


def get_daily_machine_oee(machine, date):
    """ Takes a machine id and a dates, then gets the oee for the day and saves the figure to database """
    daily_machine_oee = DailyOEE.query.filter_by(machine_id=machine.id, date=date).first()
    # If the OEE figure is missing, call the function to calculate the missing values and save in database
    if daily_machine_oee is None:
        start = datetime.combine(date=date, time=time(hour=0, minute=0, second=0, microsecond=0))
        end = start + timedelta(days=1)
        try:
            oee = calculate_machine_oee(machine, time_start=start, time_end=end)
        except OEECalculationException as e:
            current_app.logger.warn(f"Failed to calculate OEE for machine id {machine.id} on {date}")
            current_app.logger.warn(e)
            return 0
        daily_machine_oee = DailyOEE(machine_id=machine.id, date=date, oee=oee)
        db.session.add(daily_machine_oee)
        db.session.commit()

    return daily_machine_oee.oee


def get_daily_group_oee(group_id, date):
    """Get the mean OEE figure for a group of machines on a particular day"""
    group = MachineGroup.query.filter_by(id=group_id).first()
    machine_oees = []
    for machine in group.machines:
        # For each machine add the oee figure to the list
        machine_oees.append(get_daily_machine_oee(machine.id, date))
    if machine_oees is None or len(machine_oees) == 0:
        return 0
    mean_oee = sum(machine_oees) / len(machine_oees)
    return mean_oee


def get_daily_oee_dict(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's oee on the given date """
    oee_dict = get_daily_values_dict(calculate_machine_oee, requested_date)
    if human_readable:
        for k, v in oee_dict.items():
            v = v * 100
            oee_dict[k] = f"{round(v, 1)}%"
    return oee_dict
