from flask import abort
from flask_login import current_user
from functools import wraps


def admin_required(function):
    """ Decorator function to make sure the user is an admin. Functions should also be paired with @login_required"""
    @wraps(function)
    def wrapper(*args, **kwargs):
        if current_user.admin:
            return function(*args, **kwargs)
        else:
            return abort(403)

    return wrapper


