from app import db
from datetime import datetime
from flask import current_app, request
from flask_login import user_logged_in, user_logged_out
from app.login.models import User, UserSession
from app.default.models import Machine
from contextlib import contextmanager


def get_user_session(user_id):
    user_sessions = UserSession.query.filter_by(user_id=user_id, timestamp_logout=None).all()
    if len(user_sessions) == 0:
        # No user sessions yet
        return None
    if len(user_sessions) > 1:
        current_app.logger.warn(f"More than one open session for user id {user_id}")
    return user_sessions[0]


@contextmanager
def record_login(sender, user, *args, **kwargs):
    # TODO check if a user is already logged on that machine and record a logout if so
    # assigned_machine = Machine.query.filter_by(device_ip=request.remote_addr).first()
    # current_app.logger.info(f"Starting user session for {user} on {assigned_machine}")
    # new_user_session = UserSession(user_id=user.id, machine_id=assigned_machine.id)
    # db.session.add(new_user_session)
    # db.session.commit()
    pass


@contextmanager
def record_logout(sender, user, *args, **kwargs):
    # assigned_machine = Machine.query.filter_by(device_ip=request.remote_addr).first()
    # current_app.logger.info(f"Ending user session for {user} on {assigned_machine}")
    # user_session = get_user_session(user.id)
    # user_session.timestamp_logout = datetime.now().timestamp()
    # db.session.commit()
    pass


user_logged_in.connect(record_login)
user_logged_out.connect(record_logout)
