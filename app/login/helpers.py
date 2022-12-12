from datetime import datetime

from flask import current_app

from app.default import events
from app.extensions import db
from app.login.models import UserSession
from config import Config


def end_all_user_sessions(user_id=None):
    """ End all sessions, for a specific user if specified"""
    if user_id:
        sessions = UserSession.query.filter_by(user_id=user_id, active=True).all()
    else:
        sessions = UserSession.query.filter_by(active=True).all()
    for us in sessions:
        us.end_session()
