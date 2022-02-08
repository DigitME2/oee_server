from app.default.models import Job


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
        quantity_produced += job.quantity_produced
        run_time_seconds = job.end_time - job.start_time
        ideal_quantity += job.ideal_cycle_time * 1#todo
        productivity_dict[job] = get_job_oee_performance(job)

    return 1
