from datetime import datetime

from flask import current_app

from app.data_analysis.oee.availability import get_machine_runtime
from app.default.db_helpers import get_job_cropped_start_end_ratio
from app.default.models import Job


def get_machine_performance(machine_id, time_start: datetime, time_end: datetime) -> float:
    """ Get the productivity of a machine between two times, for calculating OEE"""
    machine_up_time_s = get_machine_runtime(machine_id, time_start, time_end)
    jobs = Job.query \
        .filter(Job.end_time >= time_start) \
        .filter(Job.start_time <= time_end) \
        .filter(Job.machine_id == machine_id).all()
    ideal_machine_runtime_s = 0
    for job in jobs:
        if job.ideal_cycle_time_s and job.quantity_produced:
            n, n, ratio_of_job_in_time_range = get_job_cropped_start_end_ratio(job, time_start, time_end)
            ideal_machine_runtime_s += job.ideal_cycle_time_s * (job.quantity_produced * ratio_of_job_in_time_range)
        else:
            current_app.logger.warning(f"No ideal cycle time or quantity for job {job.id}. "
                                       f"Assuming 100% Performance for this job in OEE calculation")
            ideal_machine_runtime_s += (job.end_time - job.start_time).total_seconds()
    try:
        return ideal_machine_runtime_s / machine_up_time_s
    except ZeroDivisionError:
        current_app.logger.warning(f"No uptime for machine {machine_id}. between {time_start} - {time_end}. "
                                   f"Cannot Calculate OEE")
        return 0

