from datetime import datetime

from flask import current_app

from app.data_analysis.oee.availability import get_machine_runtime
from app.default.models import Job


def get_machine_performance(machine_id, time_start: datetime, time_end: datetime) -> float:
    """ Get the productivity of a machine between two times, for calculating OEE"""
    machine_up_time_s = get_machine_runtime(machine_id, time_start, time_end, units="seconds")
    jobs = Job.query \
        .filter(Job.end_time >= time_start) \
        .filter(Job.start_time <= time_end) \
        .filter(Job.machine_id == machine_id).all()
    ideal_machine_runtime_s = 0
    for job in jobs:
        # I've already considered what happens if this job ran outside of the requested start/end and it would be ok,
        # The ratio would still be the same
        if job.ideal_cycle_time and job.quantity_produced:
            ideal_machine_runtime_s += job.ideal_cycle_time * job.quantity_produced
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

