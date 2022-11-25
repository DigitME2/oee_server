from datetime import datetime, timedelta, time

from app.default.db_helpers import get_legible_duration
from app.default.models import Machine, Job
from app.login.models import User


def get_machine_status(machine_id):
    """ Returns a dictionary holding information for the status a machine"""
    machine = Machine.query.get_or_404(machine_id)
    # Get the current user logged on to the machine
    machine_user_id = machine.current_activity.user_id
    if machine_user_id >= 0:
        machine_user_text = "No User"
    else:
        machine_user_text = User.query.get(machine_user_id).username
    activity_text = machine.current_activity.activity_code.short_description
    if machine.active_job:
        job_text = machine.current_activity.job.job_number
    else:
        job_text = "No job"
    duration = get_legible_duration(time_start=machine.current_activity.time_start,
                                    time_end=datetime.now())
    return {"machine_name": machine.name,
            "machine_user": machine_user_text,
            "machine_activity": activity_text,
            "machine_job": job_text,
            "duration": duration}


def parse_requested_machine_list(requested_machines) -> list:
    """Parse the machines selected in a dropdown list and return a list of the machine ids"""
    if requested_machines == "all":
        return list(machine.id for machine in Machine.query.all())

    # If the machines argument begins with g_ it means a group of machines has been selected
    elif requested_machines[0:2] == "g_":
        group_id = requested_machines[2:]
        return list(machine.id for machine in Machine.query.filter_by(group_id=group_id))

    # If the argument begins with m_ it represents just one machine
    elif requested_machines[0:2] == "m_":
        return list(requested_machines[2:])

    else:
        return []


def get_daily_machine_production(machine: Machine, d: datetime.date):
    """ Takes a machine and a date, then gets the total production for the day """
    start = datetime.combine(date=d, time=time(hour=0, minute=0, second=0, microsecond=0))
    end = start + timedelta(days=1)
    quantity = 0
    jobs = Job.query \
        .filter(Job.start_time <= end) \
        .filter(Job.end_time >= start) \
        .filter(Job.machine_id == machine.id).all()

    for job in jobs:
        quantity += job.quantity_produced

    return quantity


def yesterday():
    return datetime.now() - timedelta(days=1)


def today():
    return datetime.now()


def tomorrow():
    return datetime.now() + timedelta(days=1)


def a_month_ago():
    return datetime.now() - timedelta(days=28)


def a_week_ago():
    return datetime.now() - timedelta(days=7)
