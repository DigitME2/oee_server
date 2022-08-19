from datetime import datetime

from flask import current_app

from app.default.db_helpers import complete_last_activity
from app.default.models import Machine, Activity, InputDevice
from app.extensions import db
from app.login.models import UserSession
from config import Config


def start_user_session(user_id, device_id):
    """ Start a new session. Usually called when a user logs in. Fails if no machine is assigned to the device"""
    now = datetime.now()
    input_device = InputDevice.query.get(device_id)
    user_session = input_device.get_active_user_session()
    # Close any user sessions that the current user has
    if user_session is not None:
        current_app.logger.warning(
            f"Tried to start a user session for user {user_id} while one is already open. Closing...")
        end_user_sessions(user_id)
    if input_device.machine is None:
        current_app.logger.info(f"No machine assigned to {device_id}")
        return False
    # Close any sessions that exist on the current machine
    end_user_sessions(machine_id=input_device.machine.id)

    # Create the new user session
    new_us = UserSession(user_id=user_id,
                         machine_id=input_device.machine.id,
                         input_device_id=device_id,
                         time_login=now,
                         active=True)
    db.session.add(new_us)
    # Change the machine activity now that the user is logged in
    complete_last_activity(machine_id=input_device.machine.id, time_end=now)
    new_activity = Activity(machine_id=input_device.machine.id,
                            time_start=now,
                            activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                            machine_state=Config.MACHINE_STATE_OFF)
    db.session.add(new_activity)

    db.session.commit()
    current_app.logger.info(f"Started user session {new_us}")
    return True


def end_user_sessions(user_id=None, machine_id=None):
    """ End all sessions for a user or a machine (Either can be given)"""
    sessions = []
    if user_id:
        sessions.extend(UserSession.query.filter_by(user_id=user_id, active=True).all())
    elif machine_id:
        sessions.extend(UserSession.query.filter_by(machine_id=machine_id, active=True).all())
    else:
        sessions.extend(UserSession.query.filter_by(active=True).all())
    for us in sessions:
        current_app.logger.info(f"Ending user session {us}")
        us.time_logout = datetime.now()
        us.active = False
        # End all jobs assigned to the session
        for job in us.jobs:
            job.end_time = datetime.now()
            job.active = None
        db.session.commit()  # Not committing here would sometimes cause sqlite to have too many operations
        # Set the activity to "no user"
        complete_last_activity(machine_id=us.machine.id, time_end=datetime.now())
        new_activity = Activity(machine_id=us.machine.id,
                                time_start=datetime.now(),
                                activity_code_id=Config.NO_USER_CODE_ID,
                                machine_state=Config.MACHINE_STATE_OFF)
        current_app.logger.debug(f"Starting {new_activity} on logout of {us.user}")
        db.session.add(new_activity)
        db.session.commit()
