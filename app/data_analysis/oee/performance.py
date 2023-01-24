import logging
from datetime import datetime, time, timedelta, date
from typing import Tuple

from app.data_analysis.helpers import get_daily_values_dict
from app.default.helpers import get_cropped_start_end_ratio, get_jobs, get_machine_activity_duration
from app.default.models import Machine, ProductionQuantity
from config import Config


def get_machine_performance(machine: Machine, time_start: datetime, time_end: datetime) -> float:
    """ Get the productivity of a machine between two times, for calculating OEE"""
    jobs = get_jobs(time_start, time_end, machine=machine)
    ideal_machine_runtime_s = 0
    machine_uptime_during_jobs_s = 0
    for job in jobs:
        if not job.ideal_cycle_time_s:
            continue
        job_start, job_end, ratio_of_job_in_time_range = get_cropped_start_end_ratio(job, time_start, time_end)
        good_qty, reject_qty = get_production_amount(time_start, time_end, job_id=job.id)
        amount_produced = good_qty + reject_qty
        ideal_machine_runtime_s += job.ideal_cycle_time_s * amount_produced
        machine_uptime_during_jobs_s += get_machine_activity_duration(machine, job_start, job_end,
                                                                      machine_state=Config.MACHINE_STATE_UPTIME)
        machine_uptime_during_jobs_s += get_machine_activity_duration(machine, job_start, job_end,
                                                                      machine_state=Config.MACHINE_STATE_OVERTIME)
    if machine_uptime_during_jobs_s == 0:
        return 0
    performance = ideal_machine_runtime_s / machine_uptime_during_jobs_s
    if performance > 1:
        logging.warning(f"Value of performance >1 for machine ID {machine.id} on {time_start.date()}")
    return ideal_machine_runtime_s / machine_uptime_during_jobs_s


def get_production_amount(time_start, time_end, machine_id: int = None, job_id: int = None) -> Tuple[int, int]:
    good_quantity = 0
    reject_quantity = 0
    quantities_query = ProductionQuantity.query. \
        filter(ProductionQuantity.start_time <= time_end). \
        filter(ProductionQuantity.end_time >= time_start)
    if machine_id:
        quantities_query = quantities_query.filter(ProductionQuantity.machine_id == machine_id)
    if job_id:
        quantities_query = quantities_query.filter(ProductionQuantity.job_id == job_id)
    quantities = quantities_query.all()
    for q in quantities:
        # We need to adjust the quantity if the ProductionQuantity extends outside the requested range
        _, _, ratio_of_production_time_in_requested_range = get_cropped_start_end_ratio(q, time_start, time_end)
        good_quantity += (q.quantity_good * ratio_of_production_time_in_requested_range)
        reject_quantity += (q.quantity_rejects * ratio_of_production_time_in_requested_range)
    return good_quantity, reject_quantity


def get_target_production_amount(machine, time_start: datetime, time_end: datetime):
    jobs = get_jobs(time_start, time_end, machine=machine)
    ideal_production_amount = 0
    for job in jobs:
        if job.ideal_cycle_time_s:
            # Crop the time to account for a job that is halfway through
            start, end, _ = get_cropped_start_end_ratio(job, time_start, time_end)
            machine_uptime_during_jobs_s = get_machine_activity_duration(machine, start, end,
                                                                         machine_state=Config.MACHINE_STATE_UPTIME)
            ideal_production_amount += machine_uptime_during_jobs_s / job.ideal_cycle_time_s
    return ideal_production_amount


def get_daily_target_production_amount_dict(requested_date: date = None, human_readable=True):
    """ Return a dictionary with every machine's ideal production amount on the given date """
    amount_dict = get_daily_values_dict(get_target_production_amount, requested_date)
    if human_readable:
        for k, v in amount_dict.items():
            amount_dict[k] = int(v)
    return amount_dict


def get_daily_performance_dict(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's performance on the given date """
    performance_dict = get_daily_values_dict(get_machine_performance, requested_date)
    if human_readable:
        for k, v in performance_dict.items():
            v = v * 100
            performance_dict[k] = f"{round(v, 1)}%"
    return performance_dict


def get_daily_production_dict(requested_date: date = None, human_readable=True) -> Tuple[dict, dict]:
    if requested_date is None:
        requested_date = datetime.now().date()
    last_midnight = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    next_midnight = last_midnight + timedelta(days=1)
    good_amounts = {}
    reject_amounts = {}
    machines = Machine.query.all()
    for machine in machines:
        good_amounts[machine.id], reject_amounts[machine.id] = get_production_amount(time_start=last_midnight,
                                                                                     time_end=next_midnight,
                                                                                     machine_id=machine.id)
        if human_readable:
            good_amounts[machine.id] = int(good_amounts[machine.id])
            reject_amounts[machine.id] = int(reject_amounts[machine.id])
    return good_amounts, reject_amounts
