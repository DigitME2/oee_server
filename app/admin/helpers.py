import re
from functools import wraps

from flask import abort, current_app
from flask_login import current_user


def admin_required(function):
    """ Decorator function to make sure the user is an admin. Functions should also be paired with @login_required"""
    @wraps(function)
    def wrapper(*args, **kwargs):
        if current_app.config['LOGIN_DISABLED'] or current_user.admin:
            return function(*args, **kwargs)
        else:
            return abort(403)

    return wrapper


def fix_colour_code(hex_code):
    """ Checks a hex code is valid, returning a default white colour if invalid """
    # Add a hash to the start of the code if it doesn't start with one
    if hex_code[0] != "#":
        hex_code = "#" + hex_code
    # Use regular expressions to check it's a hex code
    match = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', hex_code)
    if match:
        return hex_code
    else:
        current_app.logger.warning(f"Incorrect hex code received: {hex_code}. Replacing with #FFFFFF")
        return "#FFFFFF"
