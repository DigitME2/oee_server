from datetime import datetime
from app.default.models import Machine, Activity
from app.login.models import User, UserSession
from app.db_helpers import get_legible_duration, get_current_activity_id


def get_machine_status(machine_id):
    """ Returns a dictionary holding information for the status a machine"""
    machine = Machine.query.get_or_404(machine_id)
    machine_user = User.query.get_or_404(get_current_machine_user_id(machine.id))
    current_machine_activity = Activity.query.get(get_current_activity_id(target_machine_id=machine.id))
    try:
        machine_job = current_machine_activity.job.wo_number
    except:
        machine_job = "No job"
    duration = get_legible_duration(timestamp_start=current_machine_activity.timestamp_start,
                                    timestamp_end=datetime.now().timestamp())

    return {"machine_name": machine.name,
            "machine_user": machine_user.username,
            "machine_activity": current_machine_activity.activity_code.short_description,
            "machine_job": machine_job,
            "duration": duration}

def get_current_machine_user_id(machine_id): # todo
    sessions = UserSession.filter_by(machine_id=machine_id, active=True).all()
    if len(sessions) > 1:
        current_app.logger
    elif len(sessions) == 1:
        return sessions[0].user_id
    return 1