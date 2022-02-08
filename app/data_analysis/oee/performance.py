from datetime import datetime

from flask import current_app

from app.default.models import Job


def get_machine_performance(machine_id, time_start: datetime, time_end: datetime) -> float:
    """ Get the productivity of a machine between two times, for calculating OEE"""
    jobs = Job.query \
        .filter(Job.end_time >= time_start) \
        .filter(Job.start_time <= time_end) \
        .filter(Job.machine_id == machine_id).all()
    machine_run_time_s = (time_end - time_start).total_seconds()
    total_machine_quantity_produced = 0
    ideal_machine_runtime_s = 0
    for job in jobs:
        # I've already considered what happens if this job ran outside of the requested start/end and it would be ok,
        # The ratio would still be the same
        if job.quantity_produced:
            total_machine_quantity_produced += job.quantity_produced
        job_run_time_seconds = (job.end_time - job.start_time).total_seconds()
        if job.ideal_cycle_time and job.quantity_produced:
            ideal_machine_runtime_s += job.ideal_cycle_time * job.quantity_produced
        else:
            current_app.logger.warning(f"No ideal cycle time for job {job.id}. Using actual runtime for OEE calculation")
            ideal_machine_runtime_s += job_run_time_seconds
    return ideal_machine_runtime_s / machine_run_time_s

