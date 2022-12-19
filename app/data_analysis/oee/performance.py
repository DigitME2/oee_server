import logging
from datetime import datetime, time, timedelta, date

from flask import current_app

from app.data_analysis.oee.availability import get_machine_runtime
from app.default.db_helpers import get_job_cropped_start_end_ratio, get_jobs
from app.default.models import Job, Machine


def get_machine_performance(machine: Machine, time_start: datetime, time_end: datetime) -> float:
    """ Get the productivity of a machine between two times, for calculating OEE"""
    jobs = get_jobs(time_start, time_end, machine=machine)
    ideal_machine_runtime_s = 0
    machine_uptime_during_jobs_s = 0
    for job in jobs:
        if not job.ideal_cycle_time_s:
            continue
        job_start, job_end, ratio_of_job_in_time_range = get_job_cropped_start_end_ratio(job, time_start, time_end)
        ideal_machine_runtime_s += job.ideal_cycle_time_s * (job.get_total_quantity_good() * ratio_of_job_in_time_range)
        machine_uptime_during_jobs_s += get_machine_runtime(machine, job_start, job_end)
    if machine_uptime_during_jobs_s == 0:
        return 0
    performance = ideal_machine_runtime_s / machine_uptime_during_jobs_s
    if performance > 1:
        logging.warning(f"Value of performance >1 for machine ID {machine.id} on {time_start.date()}")
    return ideal_machine_runtime_s / machine_uptime_during_jobs_s


def get_target_production_amount(machine, time_start: datetime, time_end: datetime):
    jobs = get_jobs(time_start, time_end, machine=machine)
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
        amount_dict[machine.id] = get_target_production_amount(machine, period_start, period_end)
    if human_readable:
        for k, v in amount_dict.items():
            amount_dict[k] = int(v)
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
        performance_dict[machine.id] = get_machine_performance(machine, period_start, period_end)
    if human_readable:
        for k, v in performance_dict.items():
            v = v * 100
            performance_dict[k] = f"{round(v, 1)}%"
    return performance_dict
