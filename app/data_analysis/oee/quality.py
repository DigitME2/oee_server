from datetime import datetime

from flask import current_app

from app.default.models import Job


def get_machine_quality(machine_id, time_start: datetime, time_end: datetime) -> float:
    """ Calculate the quality of machine output for calculating OEE"""
    jobs = Job.query \
        .filter(Job.end_time >= time_start) \
        .filter(Job.start_time <= time_end) \
        .filter(Job.machine_id == machine_id).all()
    total_machine_quantity_produced = 0
    total_machine_rejects_produced = 0
    for job in jobs:
        # I've already considered what happens if this job ran outside of the requested start/end and it would be ok,
        # The ratio would still be the same
        if job.quantity_produced:
            total_machine_quantity_produced += job.quantity_produced
        if job.quantity_rejects:
            total_machine_rejects_produced += job.quantity_rejects
    try:
        quality = (total_machine_quantity_produced - total_machine_rejects_produced) / total_machine_quantity_produced
        return quality
    except ZeroDivisionError:
        current_app.logger.warning(f"0 quantity produced for machine id {machine_id} "
                                   f"while calculating OEE on {time_start}."
                                   f"Skipping quality calculation...")
        return 1
