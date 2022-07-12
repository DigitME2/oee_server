import json
from datetime import datetime

from flask import request, abort

from app.default.db_helpers import complete_last_activity, get_current_machine_activity_id
from app.default.models import Job, Activity, ActivityCode
from app.extensions import db
from app.login import bp
from app.login.models import UserSession
from config import Config


@bp.route('/pausable-pause-job', methods=['POST'])
def pausable_pause_job():
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    if user_session is None:
        return json.dumps({"success": False,
                           "reason": "User is logged out"})
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=user_session.machine_id, time_end=datetime.now())

    # Start a new activity
    new_activity = Activity(machine_id=user_session.machine_id,
                            machine_state=Config.MACHINE_STATE_OFF,
                            activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                            user_id=user_session.user_id,
                            job_id=current_job.id,
                            time_start=datetime.now())
    db.session.add(new_activity)
    db.session.commit()
    return json.dumps({"success": True})


@bp.route('/pausable-resume-job', methods=['POST'])
def pausable_resume_job():
    timestamp = datetime.now().timestamp()
    # Get the reason for the pause. The app will return the short_description of the activity code
    if "downtime_reason" not in request.json:
        return json.dumps({"success": False})
    notes = request.json.get("notes", "")
    downtime_reason = request.json["downtime_reason"]
    # Get the activity code corresponding to the description
    activity_code = ActivityCode.query.filter_by(short_description=downtime_reason).first()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    time = datetime.now().strftime("%H:%M")
    if not current_job.notes:
        current_job.notes = ""  # Initialise the string if null
    if notes != "":
        current_job.notes += f"{time} - {downtime_reason} - {notes} \n"
    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=user_session.machine_id,
                           activity_code_id=activity_code.id,
                           time_end=datetime.now())

    # Start a new activity
    new_activity = Activity(machine_id=user_session.machine_id,
                            machine_state=Config.MACHINE_STATE_RUNNING,
                            activity_code_id=Config.UPTIME_CODE_ID,
                            user_id=user_session.user_id,
                            job_id=current_job.id,
                            time_start=datetime.now())
    db.session.add(new_activity)
    db.session.commit()
    return json.dumps({"success": True})


@bp.route('/pausable-android-update', methods=['POST'])
def pausable_select_activity_code():
    """ Change the activity code of the running activity, but don't end it """
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
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
