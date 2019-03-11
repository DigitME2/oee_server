from app.default.models import Activity, UNEXPLAINED_DOWNTIME_CODE
from datetime import datetime
import os

DOWNTIME_EXPLANATION_THRESHOLD_S = 600


def get_flagged_activities(current_job):
    """ Filters a list of activities and returns a list that require explanation
    from the operator"""
    # Get all activities with an unexplained downtime code
    activities = Activity.query.filter_by(job_id=current_job.id, activity_code=UNEXPLAINED_DOWNTIME_CODE).all()

    # Filter activities
    for act in activities:
        duration_s = act.timestamp_end - act.timestamp_start
        if duration_s > DOWNTIME_EXPLANATION_THRESHOLD_S:
            activities.remove(act)

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
