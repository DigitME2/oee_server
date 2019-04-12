from flask import abort
from flask_login import current_user
from functools import wraps

from app import db
from app.default.models import ActivityCode, UNEXPLAINED_DOWNTIME_CODE_ID, UPTIME_CODE_ID


def admin_required(function):
    """ Decorator function to make sure the user is an admin. Functions should also be paired with @login_required"""
    @wraps(function)
    def wrapper(*args, **kwargs):
        if current_user.admin:
            return function(*args, **kwargs)
        else:
            return abort(403)

    return wrapper


