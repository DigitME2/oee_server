from app.default.models import Job, Activity


def get_job_oee_performance(job):
    """ Get the performance of a job for calculating OEE"""
    actual_run_time_seconds = job.end_time - job.end_time
    planned_run_time_seconds = job.planned_run_time * 60
    # performance could also be planned_cycle_time x amount made
    performance = planned_run_time_seconds / actual_run_time_seconds
    return performance


def get_machine_production_amount(machine_id, requested_start, requested_end):
    """ Get the amount of products made by a """


def get_machine_performance(machine_id, requested_start, requested_end, units="seconds") -> int:
    """ Get the productivity of a machine between two times, for calculating OEE"""
    jobs = Job.query \
        .filter(Job.end_time >= requested_start) \
        .filter(Job.start_time <= requested_end) \
        .filter(Job.machine_id == machine_id).all()
    productivity_dict = {}
    quantity_produced = 0
    ideal_quantity = 0
    for job in jobs:
        # I've already considered what happens if this job ran outside of the requested start/end and it would be ok,
        # The ratio would still be the same
        quantity_produced += job.actual_quantity
        ideal_quantity += job.planned_quantity
        productivity_dict[job] = get_job_oee_performance(job)

    return 1
