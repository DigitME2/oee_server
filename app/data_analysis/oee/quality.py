import logging
from datetime import datetime, date, time, timedelta

from flask import current_app

from app.data_analysis.helpers import get_daily_values_dict
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
    if total_machine_quantity_produced == 0:
        return 0
    quality = (total_machine_quantity_produced - total_machine_rejects_produced) / total_machine_quantity_produced
    if quality > 1:
        logging.warning(f"Quality of >1 calculated for machine {machine.name} on {time_start.date()}")
    return quality


def get_daily_quality_dict(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's performance on the given date """
    quality_dict = get_daily_values_dict(get_machine_quality, requested_date)
    if human_readable:
        for k, v in quality_dict.items():
            v = v * 100
            quality_dict[k] = f"{round(v, 1)}%"
    return quality_dict
