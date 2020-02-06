from datetime import datetime

from flask import current_app

from app import db
from app.default.db_helpers import get_legible_duration, get_current_machine_activity_id
from app.default.models import Machine, Activity
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
        duration = get_legible_duration(timestamp_start=current_machine_activity.timestamp_start,
                                        timestamp_end=datetime.now().timestamp())

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
        most_recent_session = max(user_sessions, key=lambda user_session: user_session.timestamp_login)
        user_sessions.remove(most_recent_session)

        for us in user_sessions:
            current_app.logger.warning(f"Ending session {us}")
            us.timestamp_logout = datetime.now().timestamp()
            db.session.add(us)
            db.session.commit()
    elif len(user_sessions) == 1:
        return user_sessions[0].user_id
    elif len(user_sessions) == 0:
        return -1
