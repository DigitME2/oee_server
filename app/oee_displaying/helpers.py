from datetime import datetime, timedelta

from flask import current_app

from app.default.db_helpers import get_legible_duration, get_current_machine_activity_id
from app.default.models import Machine, Activity
from app.extensions import db
from app.login.models import User, UserSession


def get_machine_status(machine_id):
    """ Returns a dictionary holding information for the status a machine"""
    machine = Machine.query.get_or_404(machine_id)
    # Get the current user logged on to the machine
    machine_user_id = get_machine_current_user(machine.id)
    if machine_user_id == -1:
        machine_user_text = "No user"
    else:
        try:
            machine_user_text = User.query.get(machine_user_id).username
        except:
            current_app.logger.warning(f"Error getting user id {machine_user_id}")
            machine_user_text = "Error getting user"

    # Get the current activity on the machine
    current_activity_id = get_current_machine_activity_id(target_machine_id=machine.id)
    if current_activity_id is None:
        activity_text = "No Activity"
        job_text = "No Job"
        duration = ""
    else:
        current_machine_activity = Activity.query.get(current_activity_id)
        activity_text = current_machine_activity.activity_code.short_description
        try:
            job_text = current_machine_activity.job.wo_number
        except AttributeError:  # When there's no job
            job_text = "No job"
        duration = get_legible_duration(time_start=current_machine_activity.time_start,
                                        time_end=datetime.now())

    return {"machine_name": machine.name,
            "machine_user": machine_user_text,
            "machine_activity": activity_text,
            "machine_job": job_text,
            "duration": duration}


def get_machine_current_user(machine_id):
    """ Get the current user that is logged onto a machine"""
    user_sessions = UserSession.query.filter_by(machine_id=machine_id, active=True).all()
    # If there's more than one active session (there shouldn't be), get the most recent and end the others
    if len(user_sessions) > 1:
        current_app.logger.warning(f"Multiple user sessions found for machine id {machine_id}")
        # Get the current activity by grabbing the one with the most recent start time
        most_recent_session = max(user_sessions, key=lambda user_session: user_session.time_login)
        user_sessions.remove(most_recent_session)

        for us in user_sessions:
            current_app.logger.warning(f"Ending session {us}")
            us.time_logout = datetime.now()
            db.session.add(us)
            db.session.commit()
    elif len(user_sessions) == 1:
        return user_sessions[0].user_id
    elif len(user_sessions) == 0:
        return -1


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


def yesterday():
    return datetime.now() - timedelta(days=1)


def today():
    return datetime.now()


def tomorrow():
    return datetime.now() + timedelta(days=1)


def a_month_ago():
    return datetime.now() - timedelta(days=28)