import json
from datetime import datetime

from flask import request, abort

from app.default.db_helpers import complete_last_activity, get_current_machine_activity_id
from app.default.events import change_activity
from app.default.models import Job, Activity, ActivityCode, InputDevice
from app.extensions import db
from app.login import bp
from config import Config


@bp.route('/pausable-pause-job', methods=['POST'])
def pausable_pause_job():
    now = datetime.now()
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.active_user_session
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})
    # Start a new activity
    change_activity(now,
                    input_device.machine,
                    new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                    user_id=input_device.active_user_session.user_id,
                    job_id=input_device.machine.active_job_id)
    return json.dumps({"success": True})


@bp.route('/pausable-resume-job', methods=['POST'])
def pausable_resume_job():
    now = datetime.now()
    # Get the reason for the pause. The app will return the short_description of the activity code
    if "downtime_reason" not in request.json:
        return json.dumps({"success": False})
    notes = request.json.get("notes", "")
    downtime_reason = request.json["downtime_reason"]
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.active_user_session
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    time = datetime.now().strftime("%H:%M")
    if not current_job.notes:
        current_job.notes = ""  # Initialise the string if null
    if notes != "":
        current_job.notes += f"{time} - {downtime_reason} - {notes} \n"
    change_activity(now,
                    input_device.machine,
                    new_activity_code_id=Config.UPTIME_CODE_ID,
                    user_id=input_device.active_user_session.user_id,
                    job_id=input_device.machine.active_job_id)
    return json.dumps({"success": True})


@bp.route('/pausable-android-update', methods=['POST'])
def pausable_select_activity_code():
    """ Change the activity code of the running activity, but don't end it """
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.active_user_session
    try:
        activity_code_id = request.json["activity_code_id"]
    except KeyError:
        return json.dumps({"success": False})

    activity_code = ActivityCode.query.get(activity_code_id)
    if not activity_code:
        # This can happen if the activity code description is changed without the tablet refreshing
        # Returning a 500 will cause the tablet to refresh and get new descriptions
        return abort(500)

    # Get the last activity
    last_activity_id = get_current_machine_activity_id(user_session.machine_id)
    if last_activity_id is None:
        return abort(500)

    last_activity = db.session.query(Activity).get(last_activity_id)
    last_activity.activity_code_id = activity_code_id
    db.session.commit()

    return json.dumps({"success": True})
