import json
from datetime import datetime

import redis
from flask import request, current_app, abort

from app.android.helpers import parse_cycle_time
from app.android.workflow import PausableWorkflow, DefaultWorkflow, RunningTotalWorkflow
from app.default.db_helpers import get_current_machine_activity_id, complete_last_activity
from app.default.models import Job, Activity, ActivityCode, InputDevice, Settings
from app.extensions import db
from app.login import bp
from app.login.helpers import start_user_session, end_all_user_sessions
from app.login.models import User
from config import Config

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)


@bp.route('/check-state', methods=['GET'])
def android_check_state():
    """ The app calls this on opening, to see whether a user is logged in, or a job is active etc"""

    # Get the user session based on the device accessing this page
    uuid = request.args.get("device_uuid")
    input_device = InputDevice.query.filter_by(uuid=uuid).first()
    if not input_device:
        new_input = InputDevice(uuid=uuid, name=uuid)
        db.session.add(new_input)
        db.session.flush()
        new_input.name = "Tablet " + str(new_input.id)
        db.session.commit()
        input_device = InputDevice.query.filter_by(uuid=uuid).first()
    user_session = input_device.get_active_user_session()

    # Get the machine assigned to this device
    machine = input_device.machine

    # If there is no user session, send to the login screen. Also send here if there is no assigned machine
    if user_session is None or machine is None:
        # Show an error to the user if no machine is assigned
        if machine is None:
            machine_text = f"No assigned machine. Pair via the admin interface then press back to refresh."
        else:
            machine_text = machine.name
        return json.dumps({"workflow_type": "default",
                           "state": "no_user",
                           "machine": machine_text,
                           "device_name": input_device.name})

    current_app.logger.debug(f"Checking state for session {user_session}")
    current_app.logger.debug(f"Machine using {machine.workflow_type}")

    if machine.workflow_type == "default":
        workflow = DefaultWorkflow(user_session)

    elif machine.workflow_type == "pausable":
        workflow = PausableWorkflow(user_session)

    elif machine.workflow_type == "running_total":
        workflow = RunningTotalWorkflow(user_session)
    else:
        current_app.logger.error(f"Incorrect workflow ({machine.workflow_type}) assigned to {machine}")
        return abort(400)
    return workflow.build_server_response()


@bp.route('/android-login', methods=['POST'])
def android_login():
    """The screen to log the user into the system."""

    current_app.logger.debug("Login attempt to /android-login")
    response = {}

    uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=uuid).first()
    if not input_device:
        abort(400, message="Device not registered to server, try restarting")

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

    current_settings = Settings.query.get_or_404(1)
    if user.has_job() and not current_settings.allow_concurrent_user_jobs:
        job = Job.query.filter_by(user_id=user_id, active=True).first()
        # If this is the second attempt, end the job and log in the user
        redis_key = f"login_attempted_user_{user_id}"
        previous_login_attempt = r.get(redis_key)
        if previous_login_attempt:
            current_app.logger.info(f"Logging out user_id:{user_id}")
            r.delete(redis_key)
            job.end_time = datetime.now()
            job.active = None
            db.session.commit()
        else:
            response["success"] = False
            response["reason"] = f"User already has an active job on machine {job.machine.name}. " \
                                 f"Log in again to end this job."
            r.set(redis_key, "True", 600)
            return json.dumps(response), 200, {'ContentType': 'application/json'}

    # Check the password and log in if successful
    if user.check_password(request.get_json()["password"]):
        if not current_settings.allow_concurrent_user_jobs:
            # Log out sessions on the same user if concurrent sessions not allowed
            end_all_user_sessions(user.id)
        current_app.logger.info(f"Logged in {user} (Android)")
        response["success"] = True
        if not start_user_session(user.id, input_device.id):
            response["success"] = False
            response["reason"] = f"Error getting assigned machine (uuid={uuid})"
        return json.dumps(response), 200, {'ContentType': 'application/json'}

    else:
        response["success"] = False
        response["reason"] = "Wrong password"
        print("authentication failure")
        return json.dumps(response), 200, {'ContentType': 'application/json'}


@bp.route('/android-logout', methods=['POST'])
def android_logout():
    """ Logs the user out of the system. """
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.get_active_user_session()
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})
    # End any jobs  under the current session
    for job in user_session.jobs:
        if job.active:
            job.end_job()
    # End the current activity
    current_activity_id = get_current_machine_activity_id(input_device.machine_id)
    if current_activity_id:
        act = Activity.query.get(current_activity_id)
        act.time_end = datetime.now()
        db.session.commit()

    current_app.logger.info(f"Logging out {user_session.user}")
    user_session.end_session()
    return json.dumps({"success": True})


@bp.route('/android-start-job', methods=['POST'])
def android_start_job():
    if not request.is_json:
        return abort(400)
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.get_active_user_session()

    if not user_session:
        return abort(401)

    allow_concurrent = Settings.query.get(1).allow_concurrent_user_jobs
    machine = input_device.machine

    if not allow_concurrent and user_session.user.has_job():
        if not any(job.active for job in user_session.jobs) and any(job.active for job in machine.jobs):
            # If the active session has no job, but the machine does.
            # This should never happen, but it happened once. End the machine's session to fix it.
            end_all_user_sessions(machine_id=machine.id)
        return abort(400)

    ideal_cycle_time_s = parse_cycle_time(input_type=machine.job_start_input_type, json_data=request.json)

    if "start_time" in request.json:
        s = datetime.strptime(request.json["start_time"], "%H:%M")
        start_time = datetime.now().replace(hour=s.hour, minute=s.minute)
    else:
        start_time = datetime.now()

    # Create the job
    job = Job(start_time=start_time,
              user_id=user_session.user_id,
              user_session_id=user_session.id,
              wo_number=request.json["wo_number"],
              ideal_cycle_time_s=ideal_cycle_time_s,
              machine_id=machine.id,
              active=True)

    db.session.add(job)
    db.session.commit()

    # End the current activity
    complete_last_activity(machine_id=machine.id, time_end=start_time)

    # Set the first activity
    starting_activity_code = machine.job_start_activity_id

    # Start a new activity
    new_activity = Activity(machine_id=machine.id,
                            machine_state=Config.MACHINE_STATE_RUNNING,
                            activity_code_id=starting_activity_code,
                            user_id=user_session.user_id,
                            job_id=job.id,
                            time_start=start_time)
    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.info(f"{user_session.user} started {job}")
    return json.dumps({"success": True})


@bp.route('/android-update', methods=['POST'])
def android_update_activity():
    now = datetime.now()
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.get_active_user_session()
    try:
        activity_code_id = request.json["activity_code_id"]
    except KeyError:
        return json.dumps({"success": False})

    activity_code = ActivityCode.query.get(activity_code_id)
    if not activity_code:
        # This can happen if the activity code description is changed without the tablet refreshing
        # Returning a 500 will cause the tablet to refresh and get new descriptions
        return abort(500)

    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=input_device.machine_id, time_end=now)

    # Start a new activity
    # The current job is the only active job belonging to the user session
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    if not current_job:
        return json.dumps({"success": False, "reason": "No active job; unable to update activity"})

    # The machine state is calculated from the activity code
    if activity_code.id == Config.UPTIME_CODE_ID:
        machine_state = Config.MACHINE_STATE_RUNNING
    else:
        machine_state = Config.MACHINE_STATE_OFF
    # Create the new activity
    new_activity = Activity(machine_id=input_device.machine_id,
                            machine_state=machine_state,
                            activity_code_id=activity_code.id,
                            user_id=user_session.user_id,
                            job_id=current_job.id,
                            time_start=now)
    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.info(f"Set activity_code to {activity_code_id}")
    return json.dumps({"success": True,
                       "colour": activity_code.graph_colour})


@bp.route('/android-end-job', methods=['POST'])
def android_end_job():
    now = datetime.now()
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.get_active_user_session()
    if user_session is None:
        abort(401)
    try:
        quantity_produced = float(request.json["quantity_produced"])
        quantity_rejects = float(request.json["rejects"])
    except KeyError:
        current_app.logger.error(f"Received incorrect data from {user_session} while ending job")
        return json.dumps({"success": False,
                           "reason": "Server error parsing data"})

    # End the current job
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    if current_job is None:
        abort(400, message="No active job")
    current_job.end_time = now
    current_job.active = None

    current_job.quantity_produced += quantity_produced
    current_job.quantity_rejects += quantity_rejects

    db.session.commit()

    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=input_device.machine_id, time_end=now)

    # Start a new activity
    new_activity = Activity(machine_id=input_device.machine_id,
                            machine_state=Config.MACHINE_STATE_OFF,
                            activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                            user_id=user_session.user_id,
                            time_start=now)
    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.debug(f"User {user_session.user} ended {current_job}")
    return json.dumps({"success": True})
