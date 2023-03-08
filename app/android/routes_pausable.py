import json
import logging
from datetime import datetime

from flask import request

from app.default.events import change_activity
from app.default.models import Job, InputDevice
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
                    user_id=input_device.active_user_session.user_id)
    return json.dumps({"success": True})


@bp.route('/pausable-resume-job', methods=['POST'])
def pausable_resume_job():
    now = datetime.now()
    # Get the reason for the pause. The app will return the short_description of the activity code
    if "downtime_reason" not in request.json:
        return json.dumps({"success": False})
    component = request.json.get("component", None)
    notes = request.json.get("notes", "")
    downtime_reason = request.json["downtime_reason"]
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.active_user_session
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})
    current_job = input_device.machine.active_job
    time = datetime.now().strftime("%H:%M")
    if not current_job.notes:
        current_job.notes = ""  # Initialise the string if null
    if notes != "":
        current_job.notes += f"{time} - {downtime_reason} - {notes} \n"
    change_activity(now,
                    input_device.machine,
                    new_activity_code_id=Config.UPTIME_CODE_ID,
                    user_id=input_device.active_user_session.user_id,
                    component=component)
    return json.dumps({"success": True})


@bp.route('/pausable-android-update', methods=['POST'])
def pausable_select_activity_code():
    """ Change the activity code of the running activity, but don't end it """
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    try:
        new_activity_code_id = request.json["activity_code_id"]
    except KeyError:
        logging.error("activity_code_id not supplied to /pausable-android-update")
        return json.dumps({"success": False})

    input_device.machine.current_activity.activity_code_id = new_activity_code_id
    db.session.commit()

    return json.dumps({"success": True})
