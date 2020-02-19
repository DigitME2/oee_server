import json
from datetime import datetime

from flask import request, current_app

from app import db
from app.default.db_helpers import get_current_machine_activity_id, complete_last_activity, get_assigned_machine
from app.default.models import Job, Activity, ActivityCode
from app.login import bp
from app.login.helpers import start_user_session, end_user_sessions
from app.login.models import User, UserSession
from app.setup_database import WORKFLOW_IDS
from config import Config


@bp.route('/checkstate', methods=['GET'])
def android_check_state():
    # todo move to a method whereby different machines prompt different android_default activities
    """ The app calls this on opening, to see whether a user is logged in, or a job is active etc"""

    # Get the user session based on the IP of the device accessing this page
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()

    # Get the machine assigned to this device
    machine = get_assigned_machine(request.remote_addr)

    # If there is no user session, send to login screen. Also send here if there is no assigned machine
    if user_session is None or machine is None:
        # Show an error to the user if no machine is assigned
        if machine is None:
            machine_text = f"Error: No machine assigned to this client IP ({request.remote_addr})"
        else:
            machine_text = machine.name
        return json.dumps({"state": "no_user",
                           "machine": machine_text,
                           "ip": request.remote_addr})

    current_app.logger.debug(f"Checking state for session {user_session}")
    current_app.logger.debug(f"Starting work flow for {machine.workflow_type}")

    if machine.workflow_type_id == WORKFLOW_IDS["Default"]:
        return check_default_machine_state(user_session)

    if "android_pneumatrol" in current_app.blueprints.keys():
        from app.android_pneumatrol.routes import check_pneumatrol_machine_state
        if machine.workflow_type_id == WORKFLOW_IDS["Pneumatrol1"]:
            return check_pneumatrol_machine_state(user_session)

    #todo should remove this eventually
    else:
        return check_default_machine_state(user_session)


def check_default_machine_state(user_session):
    # If there are no active jobs on the user session, send to new job screen
    if not any(job.active for job in user_session.jobs):
        current_app.logger.debug(f"Returning state:no_job to {request.remote_addr}: no_job")
        return json.dumps({"state": "no_job"})

    # The current job is whatever job is currently active on the assigned machine
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Send the list of downtime reasons to populate a dropdown. Exclude setting and no user
    all_active_codes = ActivityCode.query.filter(ActivityCode.active,
                                                 ActivityCode.id != Config.SETTING_CODE_ID,
                                                 ActivityCode.id != Config.NO_USER_CODE_ID).all()
    # Get the current activity code to set the colour and dropdown
    try:
        machine = user_session.machine
        current_activity = Activity.query.get(get_current_machine_activity_id(machine.id))
        current_activity_code = current_activity.activity_code
        colour = current_activity_code.graph_colour
    except TypeError:
        # This could be raised if there are no activities
        current_app.logger.error(f"Active job screen requested with no activities.")
        colour = "#ffffff"
        current_activity_code = ActivityCode.query.get(Config.UNEXPLAINED_DOWNTIME_CODE_ID)

    # If the current activity is "setting", send to setting screen
    if current_activity_code.id == Config.SETTING_CODE_ID:
        return json.dumps({"state": "setting",
                           "wo_number": current_job.wo_number,
                           "colour": colour})

    current_app.logger.debug(f"Returning state: active_job to {request.remote_addr}: active_job")
    return json.dumps({"state": "active_job",
                       "wo_number": current_job.wo_number,
                       "current_activity": current_activity_code.short_description,
                       "activity_codes": [code.short_description for code in all_active_codes],
                       "colour": colour})


@bp.route('/androidlogin', methods=['POST'])
def android_login():
    """The screen to log the user into the system."""

    current_app.logger.debug("Login attempt to /androidlogin")
    response = {}

    # Return failure if correct arguments not supplied
    if "user_id" not in request.get_json():
        response["success"] = False
        response["reason"] = "No user_id supplied"
        return json.dumps(response), 200, {'ContentType': 'application/json'}
    if "password" not in request.get_json():
        response["success"] = False
        response["reason"] = "No password supplied"
        return json.dumps(response), 200, {'ContentType': 'application/json'}

    user_id = request.get_json()["user_id"]
    user = User.query.get(user_id)
    if user is None:
        response["success"] = False
        response["reason"] = f"User {user_id} does not exist"
        return json.dumps(response), 200, {'ContentType': 'application/json'}

    # Check the password and log in if successful
    if user.check_password(request.get_json()["password"]):
        # Log out sessions on the same user
        end_user_sessions(user.id)
        current_app.logger.info(f"Logged in {user} (Android)")
        response["success"] = True
        if not start_user_session(user.id, request.remote_addr):
            response["success"] = False
            response["reason"] = f"Error getting assigned machine ({request.remote_addr})"
        return json.dumps(response), 200, {'ContentType': 'application/json'}

    else:
        response["success"] = False
        response["reason"] = "Wrong password"
        print("authentication failure")
        return json.dumps(response), 200, {'ContentType': 'application/json'}


@bp.route('/androidlogout', methods=['POST'])
def android_logout():
    """ Logs the user out of the system. """
    timestamp = datetime.now().timestamp()
    # Get the current user session based on the IP of the device accessing this page
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})
    # End any jobs  under the current session
    for job in user_session.jobs:
        if job.active:
            job.end_time = timestamp
            job.active = None
    # End the current activity
    current_activity_id = get_current_machine_activity_id(user_session.machine_id)
    if current_activity_id:
        act = Activity.query.get(current_activity_id)
        act.timestamp_end = timestamp
        db.session.commit()

    current_app.logger.info(f"Logging out {user_session.user}")
    end_user_sessions(user_session.user_id)
    return json.dumps({"success": True})


@bp.route('/androidstartjob', methods=['POST'])
def android_start_job():
    if not request.is_json:
        return 404
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
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


@bp.route('/androidupdate', methods=['POST'])
def android_update_activity():
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    try:
        selected_activity_description = request.json["selected_activity_code"]
    except KeyError:
        return json.dumps({"success": False})

    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=user_session.machine_id, timestamp_end=timestamp)

    # Start a new activity
    # The current job is the only active job belonging to the user session
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # The activity code is obtained from the request
    activity_code = ActivityCode.query.filter_by(short_description=selected_activity_description).first()
    # The machine state is calculated from the activity code
    if activity_code.id == Config.UPTIME_CODE_ID:
        machine_state = Config.MACHINE_STATE_RUNNING
    else:
        machine_state = Config.MACHINE_STATE_OFF
    # Create the new activity
    new_activity = Activity(machine_id=user_session.machine_id,
                            machine_state=machine_state,
                            activity_code_id=activity_code.id,
                            user_id=user_session.user_id,
                            job_id=current_job.id,
                            timestamp_start=timestamp)
    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.debug(f"Started {new_activity} for {current_job}")
    return json.dumps({"success": True,
                       "colour": activity_code.graph_colour})


@bp.route('/androidendjob', methods=['POST'])
def android_end_job():
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()

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


