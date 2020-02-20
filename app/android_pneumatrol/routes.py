import json
from datetime import datetime

from flask import request, current_app

from app import db
from app.default.db_helpers import get_current_machine_activity_id, complete_last_activity
from app.default.models import Job, Activity, ActivityCode
from app.login import bp
from app.login.models import UserSession
from config import Config


def check_pneumatrol_machine_state(user_session):
    # If there are no active jobs on the user session, send to new job screen
    if not any(job.active for job in user_session.jobs):
        current_app.logger.debug(f"Returning state:no_job to {request.remote_addr}: no_job")
        return json.dumps({"workflow_type": "pneumatrol",
                           "state": "no_job"})

    # The current job is whatever job is currently active on the assigned machine
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Send the list of downtime reasons to populate a dropdown. Exclude setting and no user
    selectable_codes = ActivityCode.query.filter(ActivityCode.active,
                                                 ActivityCode.id != Config.SETTING_CODE_ID,
                                                 ActivityCode.id != Config.NO_USER_CODE_ID).all()
    # Get the current activity code to set the colour and dropdown
    try:
        machine = user_session.machine
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

    # If the current activity is "setting", send to setting screen
    if current_activity_code.id == Config.SETTING_CODE_ID:
        return json.dumps({"workflow_type": "pneumatrol",
                           "state": "setting",
                           "wo_number": current_job.wo_number,
                           "colour": colour})

    # If the machine is paused (indicated by the machine_state), send to pause screen
    elif current_machine_state == Config.MACHINE_STATE_OFF:
        return json.dumps({"workflow_type": "pneumatrol",
                           "state": "paused",
                           "activity_codes": [code.short_description for code in selectable_codes],
                           "wo_number": current_job.wo_number,
                           "colour": colour})

    # Otherwise send to job in progress screen
    elif current_machine_state == Config.MACHINE_STATE_RUNNING:
        current_app.logger.debug(f"Returning state: active_job to {request.remote_addr}: active_job")
        return json.dumps({"workflow_type": "pneumatrol",
                           "state": "active_job",
                           "wo_number": current_job.wo_number,
                           "current_activity": current_activity_code.short_description,
                           "colour": colour})


@bp.route('/pneumatrolstartjob', methods=['POST'])
def pneumatrol_1_start_job():
    if not request.is_json:
        return 404
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})
    machine = user_session.machine
    setting = request.json["setting"]

    # Create the job
    if setting:
        job = Job(start_time=timestamp,
                  user_id=user_session.user_id,
                  user_session_id=user_session.id,
                  wo_number=request.json["wo_number"],
                  planned_set_time=request.json["planned_set_time"],
                  machine_id=machine.id,
                  active=True)
    else:
        job = Job(start_time=timestamp,
                  user_id=user_session.user_id,
                  user_session_id=user_session.id,
                  wo_number=request.json["wo_number"],
                  planned_run_time=request.json["planned_run_time"],
                  planned_quantity=request.json["planned_quantity"],
                  planned_cycle_time=request.json["planned_cycle_time"],
                  machine_id=machine.id,
                  active=True)

    db.session.add(job)
    db.session.commit()

    # End the current activity
    complete_last_activity(machine_id=machine.id, timestamp_end=timestamp)

    # Set the first activity depending on whether the machine is being set
    if setting:
        starting_activity_code = Config.SETTING_CODE_ID
    else:
        starting_activity_code = Config.UPTIME_CODE_ID

    # Start a new activity
    new_activity = Activity(machine_id=machine.id,
                            machine_state=Config.MACHINE_STATE_RUNNING,
                            activity_code_id=starting_activity_code,
                            user_id=user_session.user_id,
                            job_id=job.id,
                            timestamp_start=timestamp)
    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.info(f"{user_session.user} started {job}")
    return json.dumps({"success": True})


@bp.route('/pneumatrolpausejob', methods=['POST'])
def pneumatrol_1_pause_job():
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    if user_session is None:
        return json.dumps({"success": False,
                           "reason": "User is logged out"})
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=user_session.machine_id, timestamp_end=timestamp)

    # Start a new activity
    new_activity = Activity(machine_id=user_session.machine_id,
                            machine_state=Config.MACHINE_STATE_OFF,
                            activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                            user_id=user_session.user_id,
                            job_id=current_job.id,
                            timestamp_start=timestamp)
    db.session.add(new_activity)
    db.session.commit()
    return json.dumps({"success": True})


@bp.route('/pneumatrolresumejob', methods=['POST'])
def pneumatrol_1_resume_job():
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
    if notes is not "":
        current_job.notes += f"{time} - {downtime_reason} - {notes} \n"
    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=user_session.machine_id,
                           activity_code_id=activity_code.id,
                           timestamp_end=timestamp)

    # Start a new activity
    new_activity = Activity(machine_id=user_session.machine_id,
                            machine_state=Config.MACHINE_STATE_RUNNING,
                            activity_code_id=Config.UPTIME_CODE_ID,
                            user_id=user_session.user_id,
                            job_id=current_job.id,
                            timestamp_start=timestamp)
    db.session.add(new_activity)
    db.session.commit()
    return json.dumps({"success": True})


@bp.route('/pneumatrolendjob', methods=['POST'])
def pneumatrol_1_end_job():
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})

    try:
        quantity = int(request.json["quantity"])
        setting = request.json["setting"]
    except KeyError:
        return json.dumps({"success": False})

    # End the current job
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    current_job.end_time = timestamp
    current_job.active = None

    # If the job was being set, quantity = the scrap, otherwise it is actual quantity
    if setting:
        current_job.setup_scrap = quantity
    else:
        current_job.actual_quantity = quantity

    db.session.commit()

    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=user_session.machine_id, timestamp_end=timestamp)

    # Start a new activity
    new_activity = Activity(machine_id=user_session.machine_id,
                            machine_state=Config.MACHINE_STATE_OFF,
                            activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                            user_id=user_session.user_id,
                            timestamp_start=timestamp)
    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.debug(f"User {user_session.user} ended {current_job}")
    return json.dumps({"success": True})



