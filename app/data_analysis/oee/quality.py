import logging
from datetime import datetime, date, time, timedelta

from flask import current_app

from app.default.helpers import get_jobs
from app.default.models import Machine


def get_machine_quality(machine: Machine, time_start: datetime, time_end: datetime) -> float:
    """ Calculate the quality of machine output for calculating OEE"""
    jobs = get_jobs(time_start, time_end, machine=machine)
    total_machine_quantity_produced = 0
    total_machine_rejects_produced = 0
    for job in jobs:
        # I've already considered what happens if this job ran outside the requested start/end, and it would be ok,
        # All we can do is assume the job has same performance all the way through, so the ratio would still be the same
        rejects_qty = job.get_total_reject_quantity()
        good_qty = job.get_total_good_quantity()
        total_machine_quantity_produced += (good_qty + rejects_qty)
        total_machine_rejects_produced += rejects_qty
    try:
        quality = (total_machine_quantity_produced - total_machine_rejects_produced) / total_machine_quantity_produced
        if quality > 1:
            logging.warning(f"Quality of >1 calculated for machine {machine.name} on {time_start.date()}")
        return quality
    except ZeroDivisionError:
        current_app.logger.warning(f"0 quantity produced for machine {machine.name} "
                                   f"while calculating OEE on {time_start}."
                                   f"Skipping quality calculation...")
        return 1


def get_daily_quality_dict(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's performance on the given date """
    if not requested_date:
        requested_date = datetime.now().date()
    # Use 00:00 and 24:00 on the selected day
    period_start = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    period_end = period_start + timedelta(days=1)
    # If the end is in the future, change to now
    if period_end > datetime.now():
        period_end = datetime.now()
    quality_dict = {}
    for machine in Machine.query.all():
        quality_dict[machine.id] = get_machine_quality(machine, period_start, period_end)
    if human_readable:
        for k, v in quality_dict.items():
            v = v * 100
            quality_dict[k] = f"{round(v, 1)}%"
    return quality_dict
