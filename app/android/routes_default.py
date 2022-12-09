import json
from datetime import datetime

import redis
from flask import request, current_app, abort

from app.android.helpers import parse_cycle_time
from app.android.workflow import PausableWorkflow, DefaultWorkflow, RunningTotalWorkflow
from app.default import events
from app.default.models import Job, InputDevice, Settings
from app.extensions import db
from app.login import bp
from app.login.helpers import end_all_user_sessions
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
        # Add the new device if it doesn't exist in the database
        new_input = InputDevice(uuid=uuid, name=uuid)
        db.session.add(new_input)
        db.session.flush()
        new_input.name = "Tablet " + str(new_input.id)
        db.session.commit()
        input_device = InputDevice.query.filter_by(uuid=uuid).first()
    user_session = input_device.active_user_session

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
    now = datetime.now()
    response = {}

    uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=uuid).first()
    if not input_device:
        abort(400, message="Device not registered to server, try restarting")

    # Return failure if correct arguments not supplied
    if "user_id" not in request.get_json():
        response["success"] = False
        response["reason"] = "No user_id supplied"
        return json.dumps(response), 400, {'ContentType': 'application/json'}
    if "password" not in request.get_json():
        response["success"] = False
        response["reason"] = "No password supplied"
        return json.dumps(response), 400, {'ContentType': 'application/json'}

    user_id = request.get_json()["user_id"]
    user = User.query.get(user_id)

    if user is None:
        response["success"] = False
        response["reason"] = f"User {user_id} does not exist"
        return json.dumps(response), 401, {'ContentType': 'application/json'}

    current_settings = Settings.query.get_or_404(1)
    if len(user.active_input_devices) > 0 and not current_settings.allow_concurrent_user_jobs:
        # Warn if the user is already logged in (and this is not allowed)
        job = Job.query.filter_by(user_id=user_id, active=True).first()
        # If this is the second attempt, end the job and log in the user
        redis_key = f"login_attempted_user_{user_id}"
        previous_login_attempt = r.get(redis_key)
        if previous_login_attempt:
            events.android_log_out(input_device, now)
            r.delete(redis_key)
        else:
            response["success"] = False
            response["reason"] = f"User already has an active job on machine {job.machine.name}. " \
                                 f"Log in again to end this job."
            r.set(redis_key, "True", 600)
            return json.dumps(response), 200, {'ContentType': 'application/json'}

    # Check the password and log in if successful
    if not user.check_password(request.get_json()["password"]):
        response["success"] = False
        response["reason"] = "Wrong password"
        print("authentication failure")
        return json.dumps(response), 400, {'ContentType': 'application/json'}
    if not current_settings.allow_concurrent_user_jobs:
        # Log out sessions on the same user if concurrent sessions not allowed
        end_all_user_sessions(user.id)
    current_app.logger.info(f"Logged in {user} (Android)")
    success = events.android_log_in(now, user, input_device)
    if success:
        response["success"] = True
        status_code = 200
    else:
        response["success"] = False
        response["reason"] = "No assigned machine"
        status_code = 400
    return json.dumps(response), status_code, {'ContentType': 'application/json'}


@bp.route('/android-logout', methods=['POST'])
def android_logout():
    """ Logs the user out of the system. """
    now = datetime.now()
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.active_user_session
    if user_session is None:
        return json.dumps({"success": False, "reason": "User is logged out"})
    events.android_log_out(input_device, now)
    return json.dumps({"success": True})


@bp.route('/android-start-job', methods=['POST'])
def android_start_job():
    if not request.is_json:
        return abort(400)
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    if not input_device.active_user_session:
        return abort(401)

    ideal_cycle_time_s = parse_cycle_time(input_type=input_device.machine.job_start_input_type, json_data=request.json)
    # The device can request a different start time
    if "start_time" in request.json:
        s = datetime.strptime(request.json["start_time"], "%H:%M")
        start_time = datetime.now().replace(hour=s.hour, minute=s.minute)
    else:
        start_time = datetime.now()
    events.start_job(dt=start_time,
                     machine=input_device.machine,
                     user_id=input_device.active_user_session.user_id,
                     job_number=request.json["job_number"],
                     ideal_cycle_time_s=ideal_cycle_time_s)
    return json.dumps({"success": True})


@bp.route('/android-update', methods=['POST'])
def android_update_activity():
    now = datetime.now()
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    if not input_device.active_user_session:
        return json.dumps({"success": False})
    try:
        activity_code_id = request.json["activity_code_id"]
    except KeyError:
        current_app.logger.warning("Failed to get activity code ID from POST to android-update")
        return json.dumps({"success": False})

    events.change_activity(now,
                           input_device.machine,
                           new_activity_code_id=activity_code_id,
                           user_id=input_device.active_user_session.user_id,
                           job_id=input_device.machine.active_job_id)

    current_app.logger.info(f"Set activity_code to {activity_code_id}")
    return json.dumps({"success": True})


@bp.route('/android-end-job', methods=['POST'])
def android_end_job():
    now = datetime.now()
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.active_user_session
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
    current_job = input_device.machine.active_job
    if current_job is None:
        abort(400, message="No active job")
    events.end_job(now, current_job, quantity_produced, quantity_rejects)
    input_device.machine.active_job_id = None
    db.session.commit()
    # Set the activity to downtime
    events.change_activity(dt=now,
                           machine=input_device.machine,
                           new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                           user_id=user_session.user_id,
                           job_id=current_job.id)
    events.produced(now, quantity_produced, quantity_rejects, current_job.id, input_device.machine.id)
    return json.dumps({"success": True})
