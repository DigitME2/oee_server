import logging
from datetime import datetime, time, timedelta, date

from flask import current_app

from app.data_analysis.oee.availability import get_machine_runtime
from app.default.db_helpers import get_job_cropped_start_end_ratio, get_machine_jobs
from app.default.models import Job, Machine


def get_machine_performance(machine_id, time_start: datetime, time_end: datetime) -> float:
    """ Get the productivity of a machine between two times, for calculating OEE"""
    machine_up_time_s = get_machine_runtime(machine_id, time_start, time_end)
    jobs = get_machine_jobs(machine_id, time_start, time_end)
    ideal_machine_runtime_s = 0
    for job in jobs:
        if job.ideal_cycle_time_s and job.quantity_produced:
            _, _, ratio_of_job_in_time_range = get_job_cropped_start_end_ratio(job, time_start, time_end)
            ideal_machine_runtime_s += job.ideal_cycle_time_s * (job.quantity_produced * ratio_of_job_in_time_range)
        else:
            current_app.logger.warning(f"No ideal cycle time or quantity for job {job.id}. "
                                       f"Assuming 100% Performance for this job in OEE calculation")
            ideal_machine_runtime_s += (job.end_time - job.start_time).total_seconds()
    try:
        performance = ideal_machine_runtime_s / machine_up_time_s
        if performance > 1:
            logging.warning(f"Value of performance >1 for machine ID {machine_id} on {time_start.date()}")
        return ideal_machine_runtime_s / machine_up_time_s
    except ZeroDivisionError:
        current_app.logger.warning(f"No uptime for machine {machine_id}. between {time_start} - {time_end}. "
                                   f"Cannot Calculate OEE")
        return 0


def get_target_production_amount(machine_id, time_start: datetime, time_end: datetime):
    jobs = get_machine_jobs(machine_id, time_start, time_end)
    ideal_production_amount = 0
    for job in jobs:
        if job.ideal_cycle_time_s:
            # Crop the time to account for a job that is halfway through
            start, end, _ = get_job_cropped_start_end_ratio(job, time_start, time_end)
            adjusted_job_length_s = (end - start).total_seconds()
            ideal_production_amount += adjusted_job_length_s / job.ideal_cycle_time_s
    return ideal_production_amount


def get_daily_target_production_amount_dict(requested_date: date = None, human_readable=True):
    """ Return a dictionary with every machine's ideal production amount on the given date """
    if not requested_date:
        requested_date = datetime.now().date()
    # Use 00:00 and 24:00 on the selected day
    period_start = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    period_end = period_start + timedelta(days=1)
    # If the end is in the future, change to now
    if period_end > datetime.now():
        period_end = datetime.now()
    amount_dict = {}
    for machine in Machine.query.all():
        amount_dict[machine.id] = get_target_production_amount(machine.id, period_start, period_end)
    if human_readable:
        for k, v in amount_dict.items():
            amount_dict[k] = f"{round(v, 0)}"
    return amount_dict


def get_daily_performance_dict(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's performance on the given date """
    if not requested_date:
        requested_date = datetime.now().date()
    # Use 00:00 and 24:00 on the selected day
    period_start = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    period_end = period_start + timedelta(days=1)
    # If the end is in the future, change to now
    if period_end > datetime.now():
        period_end = datetime.now()
    performance_dict = {}
    for machine in Machine.query.all():
        performance_dict[machine.id] = get_machine_performance(machine.id, period_start, period_end)
    if human_readable:
        for k, v in performance_dict.items():
            v = v * 100
            performance_dict[k] = f"{round(v, 1)}%"
    return performance_dict
# TODO We need to clarify whether production amount includes rejects (i.e. total amount) and change the naming scheme, and make sure it is followed throughout.
