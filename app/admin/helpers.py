from datetime import datetime, time
import re
from functools import wraps

from flask import abort, current_app, flash
from flask_login import current_user

from app import db
from app.default.models import ShiftPeriod, SHIFT_STRFTIME_FORMAT
from config import Config


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


def create_shift_day(day: str, shift_start: str, shift_end: str, shift_id: int):
    """ Creates 3 ShiftPeriod entries for a standard day of one shift"""
    midnight = time(0, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
    period_1 = ShiftPeriod(shift_id=shift_id, shift_state=Config.MACHINE_STATE_PLANNED_DOWNTIME,
                           day=day, start_time=midnight)
    db.session.add(period_1)
    period_2 = ShiftPeriod(shift_id=shift_id, shift_state=Config.MACHINE_STATE_UPTIME,
                           day=day, start_time=shift_start)
    db.session.add(period_2)
    period_3 = ShiftPeriod(shift_id=shift_id, shift_state=Config.MACHINE_STATE_PLANNED_DOWNTIME,
                           day=day, start_time=shift_end)
    db.session.add(period_3)
    db.session.commit()


def save_shift_form(form, shift):
    shift.name = form.name.data
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        periods = [p for p in shift.shift_periods if p.day == day]
        disable_day_input = getattr(form, day + "_disable")
        if disable_day_input.data:
            # If "no shifts" is marked for this day, delete all the day's shift periods and continue
            for period in periods:
                db.session.delete(period)
            continue
        start_time_str = getattr(form, day + "_start").data.strftime(SHIFT_STRFTIME_FORMAT)
        end_time_str = getattr(form, day + "_end").data.strftime(SHIFT_STRFTIME_FORMAT)
        if len(periods) == 0:
            # If creating the day's shifts for the first time
            create_shift_day(day, start_time_str, end_time_str, shift.id)
            continue
        if len(periods) != 3:
            # This function only works with 3 shift periods per day
            raise ModifiedShiftException
        periods.sort(key=lambda p: int(p.start_time))
        periods[1].start_time = start_time_str
        periods[2].start_time = end_time_str
        if periods[2].start_time < periods[1].start_time:
            db.session.rollback()
            flash(f"Shift end before shift start for {day}")
            return abort(400)
    db.session.commit()
    return shift


def load_shift_form_values(form, shift):
    form.name.data = shift.name
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        periods = [p for p in shift.shift_periods if p.day == day]
        if len(periods) == 0:
            disable_day_input = getattr(form, day + "_disable")
            disable_day_input.data = True
            continue
        if len(periods) != 3:
            # This function only works with 3 shift periods per day
            raise ModifiedShiftException
        periods.sort(key=lambda p: int(p.start_time))
        start_form_input = getattr(form, day + "_start")
        start_form_input.data = datetime.strptime(periods[1].start_time, SHIFT_STRFTIME_FORMAT)
        end_form_input = getattr(form, day + "_end")
        end_form_input.data = datetime.strptime(periods[2].start_time, SHIFT_STRFTIME_FORMAT)
    return form


class ModifiedShiftException(Exception):
    pass
