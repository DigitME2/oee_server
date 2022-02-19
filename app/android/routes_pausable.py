import json
from datetime import datetime

from flask import request, current_app

from app.android.helpers import REQUESTED_DATA_JOB_END, REQUESTED_DATA_JOB_START
from app.default.db_helpers import get_current_machine_activity_id, complete_last_activity
from app.default.models import Job, Activity, ActivityCode
from app.extensions import db
from app.login import bp
from app.login.models import UserSession
from config import Config


def check_pausable_machine_state(user_session):
    # If there are no active jobs on the user session, send to new job screen
    machine = user_session.machine
    if not any(job.active for job in user_session.jobs):
        return json.dumps({"workflow_type": "pausable",
                           "state": "no_job",
                           "requested_data": REQUESTED_DATA_JOB_START})

    # The current job is whatever job is currently active on the assigned machine
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Send the list of downtime reasons to populate a dropdown. Exclude up and no user
    selectable_codes = ActivityCode.query.filter(ActivityCode.active,
                                                 ActivityCode.id != Config.UPTIME_CODE_ID,
                                                 ActivityCode.id != Config.NO_USER_CODE_ID).all()
    # Get the current activity code to set the colour and dropdown
    try:
        current_activity = Activity.query.get(get_current_machine_activity_id(machine.id))
        current_activity_code = current_activity.activity_code
        current_machine_state = current_activity.machine_state
        colour = current_activity_code.graph_colour
    except TypeError:
        # This could be raised if there are no activities
        current_app.logger.error(f"Active job screen requested with no activities.")
        colour = "#ffffff"
        current_activity_code = ActivityCode.query.get(Config.UNEXPLAINED_DOWNTIME_CODE_ID)
        current_machine_state = Config.MACHINE_STATE_OFF

    # If the machine is paused (indicated by the machine_state), send to pause screen
    if current_machine_state == Config.MACHINE_STATE_OFF:
        return json.dumps({"workflow_type": "pausable",
                           "state": "paused",
                           "activity_codes": [code.short_description for code in selectable_codes],
                           "wo_number": current_job.wo_number,
                           "colour": colour})

    # Otherwise send to job in progress screen
    elif current_machine_state == Config.MACHINE_STATE_RUNNING:
        current_app.logger.debug(f"Returning state: active_job to {request.remote_addr}: active_job")
        return json.dumps({"workflow_type": "pausable",
                           "state": "active_job",
                           "wo_number": current_job.wo_number,
                           "current_activity": current_activity_code.short_description,
                           "colour": colour,
                           "requested_data_on_end": REQUESTED_DATA_JOB_END})


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

