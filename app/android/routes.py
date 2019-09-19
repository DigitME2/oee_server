import json
from datetime import datetime

from flask import request, redirect, current_app

from app import db
from app.android.helpers import start_user_session, end_user_sessions
from app.db_helpers import get_current_activity_id, complete_last_activity
from app.default.models import Machine, Job, Activity, ActivityCode
from app.login import bp
from app.login.models import User, UserSession

from config import Config


# TODO Get rid of pauses. Maybe branch to do this
# TODO Check the request makes sense, ie ensure the app hasnt got to the wrong page


@bp.route('/checkstate', methods=['GET'])
def android_check_state():
    """ The app calls this on opening, to see whether a user is logged in, or a job is active etc"""
    # Get the user session based on the IP of the device accessing this page
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    # If there is no user session, send to login screen
    if user_session is None:
        current_app.logger.debug(f"Returning state to {request.remote_addr}: no_user")
        return json.dumps({"state": "no_user"})

    current_app.logger.debug(f"Checking state for session {user_session}")
    # If there are no active jobs on the user session, send to new job screen
    if not any(job.active for job in user_session.jobs):
        current_app.logger.debug(f"Returning state to {request.remote_addr}: no_job")
        return json.dumps({"state": "no_job"})

    # The current job is whatever job is currently active on the assigned machine
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Send the list of downtime reasons to populate a dropdown
    all_codes = ActivityCode.query.filter_by(active=True).all()
    downtime_reasons = [code.short_description for code in all_codes]

    # Send a list of colours corresponding to downtime reasons
    colours = [code.graph_colour for code in all_codes]
    # TODO Do the lists of colours and downtime become misaligned if activity codes get disabled?
    colours = [code.graph_colour for code in all_codes]
    # If the most recent activity is "running", send to active job screen. Attach the wo_number to display to user
    try:
        machine = user_session.machine
        current_activity = Activity.query.get(get_current_activity_id(machine.id))
        machine_state = current_activity.machine_state
    except TypeError:
        # This could be raised if there are no activities
        current_app.logger.debug(f"Returning state to {request.remote_addr}: active_job")
        return json.dumps({"state": "active_job",
                           "wo_number": current_job.wo_number,
                           "downtime_reasons": downtime_reasons,
                           "colours": colours})
    if machine_state == Config.MACHINE_STATE_RUNNING:
        current_app.logger.debug(f"Returning state to {request.remote_addr}: active_job")
        return json.dumps({"state": "active_job",
                           "wo_number": current_job.wo_number,
                           "downtime_reasons": downtime_reasons,
                           "colours": colours})
    # If the most recent activity is not uptime, send to paused job screen. Send downtime reasons for dropdown box
    else:
        all_codes = ActivityCode.query.filter_by(active=True).all()
        downtime_reasons = [code.short_description for code in all_codes]
        colours = [code.graph_colour for code in all_codes]
        current_app.logger.debug(f"Returning state to {request.remote_addr}: paused_job")
        return json.dumps({"state": "paused_job",
                           "wo_number": current_job.wo_number,
                           "downtime_reasons": downtime_reasons,
                           "colours": colours})


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
        start_user_session(user.id, request.remote_addr)
        return json.dumps(response), 200, {'ContentType': 'application/json'}

    else:
        response["success"] = False
        response["reason"] = "Wrong password"
        print("authentication failure")
        return json.dumps(response), 200, {'ContentType': 'application/json'}


@bp.route('/androidlogout', methods=['POST'])
def android_logout():
    """ Logs the user out of the system. """
    # Get the current user session based on the IP of the device accessing this page
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    # End any jobs under the current session
    for job in user_session.jobs:
        if job.active:
            job.end_time = datetime.now().timestamp()
            job.active = None
    current_app.logger.info(f"Logging out {user_session.user}")
    end_user_sessions(user_session.user_id)
    return json.dumps({"success": True})


@bp.route('/androidstartjob', methods=['POST'])
def android_start_job():
    if not request.is_json:
        return 404
    machine = Machine.query.filter_by(device_ip=request.remote_addr).first()
    if machine is None:
        # TODO Properly account for a machine not being assigned
        machine = Machine.query.get(1)
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()

    # Create the job
    job = Job(start_time=datetime.now().timestamp(),
              user_id=user_session.user_id,
              user_session_id=user_session.id,
              wo_number=request.json["wo_number"],
              planned_cycle_time=request.json["planned_cycle_time"],
              planned_cycle_quantity=request.json["planned_cycle_quantity"],
              machine_id=machine.id,
              active=True)
    db.session.add(job)
    db.session.commit()

    # End the current activity
    complete_last_activity(machine_id=machine.id)

    # Start a new activity
    new_activity = Activity(machine_id=machine.id,
                            machine_state=Config.MACHINE_STATE_RUNNING,
                            activity_code_id=Config.UPTIME_CODE_ID,
                            user_id=user_session.user_id,
                            job_id=job.id,
                            timestamp_start=datetime.now().timestamp())
    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.info(f"{user_session.user} started {job}")
    return json.dumps({"success": True})


@bp.route('/androidpausejob', methods=['POST'])
def android_pause_job():
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
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
    current_app.logger.debug(f"Paused {current_job}")

    downtime_reasons = [code.short_description for code in ActivityCode.query.filter_by(active=True).all()]
    return json.dumps({"success": True,
                       "wo_number": current_job.wo_number,
                       "downtime_reasons": downtime_reasons})


@bp.route('/androidresumejob', methods=['POST'])
def android_resume_job():
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=user_session.machine_id, timestamp_end=timestamp)

    # Start a new activity
    new_activity = Activity(machine_id=user_session.machine_id,
                            machine_state=Config.MACHINE_STATE_RUNNING,
                            activity_code_id=Config.UPTIME_CODE_ID,
                            user_id=user_session.user_id,
                            job_id=current_job.id,
                            timestamp_start=timestamp)
    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.debug(f"Resumed {current_job}")
    return json.dumps({"success": True,
                       "wo_number": current_job.wo_number})


@bp.route('/androidupdate', methods=['POST'])
def android_update_activity():
    """ Updates the activity code of the current activity without starting a new one"""
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()

    reason = request.json["downtime_reason"]

    # Update the current activity
    current_activity = Activity.query.get(get_current_activity_id(user_session.machine_id))
    activity_code = ActivityCode.query.filter_by(short_description=reason).first()
    current_activity.activity_code_id = activity_code.id
    db.session.commit()
    return json.dumps({"success": True})


@bp.route('/androidendjob', methods=['POST'])
def android_end_job():
    timestamp = datetime.now().timestamp()
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()

    # End the current job
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    current_job.timestamp_end = timestamp
    current_job.active = None

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
    current_app.logger.debug(f"Ended {current_job}")
    return json.dumps({"success": True})


