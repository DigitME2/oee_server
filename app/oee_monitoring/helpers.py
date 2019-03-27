from app import db
from app.default.models import UNEXPLAINED_DOWNTIME_CODE_ID, UPTIME_CODE_ID, MACHINE_STATE_RUNNING
from datetime import datetime
import os

DOWNTIME_EXPLANATION_THRESHOLD_S = 2  # todo set this to a reasonable number after testing


def flag_activities(activities):
    """ Filters a list of activities, adding explanation_required=True to those that require an explanation
    for downtime above a defined threshold"""

    ud_index_counter = 0
    for act in activities:
        # Only Flag activities with the downtime code and with a duration longer than the threshold
        if act.activity_code_id == UNEXPLAINED_DOWNTIME_CODE_ID and \
                (act.timestamp_end - act.timestamp_start) > DOWNTIME_EXPLANATION_THRESHOLD_S:
            act.explanation_required = True
            # Give the unexplained downtimes their own index
            act.ud_index = ud_index_counter
            ud_index_counter += 1
        else:
            act.explanation_required = False
    db.session.commit()
    return activities


def get_legible_downtime_time(timestamp_start, timestamp_end):
    """ Takes two timestamps and returns a string in the format <hh:mm> <x> minutes"""
    start = datetime.fromtimestamp(timestamp_start).strftime('%H:%M')
    length_m = int((timestamp_end - timestamp_start) / 60)
    s = "{start_time} for {length_minutes} minutes".format(start_time=start, length_minutes=str(length_m))

    # Measures downtime in seconds instead of minutes for testing purposes
    if os.environ.get("FLASK_DEBUG", default=False) == "1":
        # todo delete this, not needed for production
        start = datetime.fromtimestamp(timestamp_start).strftime('%H:%M:%S')
        s = "{start_time} for {length_seconds} seconds".format(
            start_time=start,
            length_seconds=int(timestamp_end - timestamp_start))

    return s
