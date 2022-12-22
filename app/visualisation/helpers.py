from datetime import datetime, timedelta, time

from app.default.helpers import get_legible_duration, get_jobs
from app.default.models import Machine, Job
from app.login.models import User


def get_machine_status(machine: Machine):
    """ Returns a dictionary holding information for the status a machine"""
    # Get the current user logged on to the machine
    machine_user_id = machine.current_activity.user_id
    if not machine_user_id or machine_user_id <= 0:
        machine_user_text = "No User"
    else:
        machine_user_text = User.query.get(machine_user_id).username
    activity_text = machine.current_activity.activity_code.short_description
    if machine.active_job:
        job_text = machine.current_activity.job.job_number
    else:
        job_text = "No job"
    duration = get_legible_duration(time_start=machine.current_activity.start_time,
                                    time_end=datetime.now())
    return {"machine_name": machine.name,
            "machine_user": machine_user_text,
            "machine_activity": activity_text,
            "machine_job": job_text,
            "duration": duration}


def parse_requested_machine_list(requested_machines) -> list[Machine]:
    """Parse the machines selected in a dropdown list and return a list of the machines"""
    if requested_machines == "all":
        return Machine.query.all()

    # If the machines argument begins with g_ it means a group of machines has been selected
    elif requested_machines[0:2] == "g_":
        group_id = requested_machines[2:]
        return Machine.query.filter_by(group_id=group_id).all()

    # If the argument begins with m_ it represents just one machine
    elif requested_machines[0:2] == "m_":
        machine_id = int(requested_machines[2:])
        return list(Machine.query.get_or_404(machine_id))
    else:
        return []


def get_daily_machine_production(machine: Machine, d: datetime.date):
    """ Takes a machine and a date, then gets the total production for the day """
    start = datetime.combine(date=d, time=time(hour=0, minute=0, second=0, microsecond=0))
    end = start + timedelta(days=1)
    quantity = 0
    jobs = get_jobs(start, end, machine=machine)
    for job in jobs:
        quantity += job.get_total_quantity_good()

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
