from datetime import date, datetime, timedelta, time

import humanize

from app.default.models import Machine


def get_daily_values_dict(func, requested_date: date = None):
    """ Runs the given function for every machine and returns a dict with its values"""
    if not requested_date:
        requested_date = datetime.now().date()
    # Use 00:00 and 24:00 on the selected day
    period_start = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    period_end = period_start + timedelta(days=1)
    # If the end is in the future, change to now
    if period_end > datetime.now():
        period_end = datetime.now()
    values = {}
    for machine in Machine.query.all():
        values[machine.id] = func(machine, period_start, period_end)
    return values


def durations_dict_to_human_readable(d):
    """Given a dict of durations, formats all the values to a human-readable format"""
    for k, v in d.items():
        if v < 60:
            humanize_format = "%0.1f"
        else:
            humanize_format = "%0.0f"
        v = humanize.precisedelta(timedelta(seconds=v), minimum_unit="minutes", format=humanize_format)
        d[k] = v
