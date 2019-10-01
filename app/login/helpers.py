from datetime import datetime

from flask import current_app

from app import db
from app.default.models import Machine
from app.login.models import UserSession


def start_user_session(user_id, device_ip):
    user_session = UserSession.query.filter_by(user_id=user_id, device_ip=device_ip, active=True).first()
    if user_session is not None:
        current_app.logger.warning(
            f"Tried to start a user session for user {user_id} while one is already open. Closing...")
        end_user_sessions(user_id)
    try:
        machine_id = Machine.query.filter_by(device_ip=device_ip).first().id
    except:
        current_app.logger.info(f"No machine assigned to {device_ip}")
        machine_id = 1  # todo
    us = UserSession(user_id=user_id,
                     machine_id=machine_id,
                     device_ip=device_ip,
                     timestamp_login=datetime.now().timestamp(),
                     active=True)
    db.session.add(us)
    db.session.commit()
    current_app.logger.debug(f"Starting user session {us}")


def end_user_sessions(user_id):
    timestamp = datetime.now().timestamp()
    sessions = UserSession.query.filter_by(user_id=user_id, active=True).all()
    for us in sessions:
        current_app.logger.debug(f"Ending user session {us}")
        us.timestamp_logout = timestamp
        us.active = False
        # End all jobs assigned to the session
        for job in us.jobs:
            job.end_time = timestamp
            job.active = None
        db.session.commit()