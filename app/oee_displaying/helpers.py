from datetime import datetime
from app.default.models import Machine, Activity
from app.login.models import User
from app.db_helpers import get_current_machine_user_id, get_legible_duration, get_current_activity_id


def get_machine_status(machine_id):
    """ Returns a dictionary holding different values for a machine"""
    machine = Machine.query.get_or_404(machine_id)
    machine_user = User.query.get_or_404(get_current_machine_user_id(machine.id))
    current_machine_activity = Activity.query.get(get_current_activity_id(target_machine_id=machine.id))
    duration = get_legible_duration(timestamp_start=current_machine_activity.timestamp_start,
                                    timestamp_end=datetime.now().timestamp())

    return {"machine_name": machine.name,
            "machine_user": machine_user.username,
            "machine_activity": current_machine_activity.activity_code.short_description,
            "machine_job": current_machine_activity.job,
            "duration": duration}
