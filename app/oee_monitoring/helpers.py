from random import randrange
from app import db
from app.default.models import UPTIME_CODE_ID, UNEXPLAINED_DOWNTIME_CODE_ID, Activity, MACHINE_STATE_OFF, \
    MACHINE_STATE_RUNNING, Settings
from datetime import datetime


def flag_activities(activities):
    """ Filters a list of activities, adding explanation_required=True to those that require an explanation
    for downtime above a defined threshold"""

    ud_index_counter = 0
    downtime_explanation_threshold_s = Settings.query.get_or_404(1).threshold
    for act in activities:
        # Only Flag activities with the downtime code and with a duration longer than the threshold
        if act.activity_code_id == UNEXPLAINED_DOWNTIME_CODE_ID and \
                (act.timestamp_end - act.timestamp_start) > downtime_explanation_threshold_s:
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

    # Show in seconds if the run time is less than a minute
    if (timestamp_end - timestamp_start) < 60:
        start = datetime.fromtimestamp(timestamp_start).strftime('%H:%M:%S')
        s = "{start_time} for {length_seconds} seconds".format(
            start_time=start,
            length_seconds=int(timestamp_end - timestamp_start))

    return s


def get_dummy_machine_activity(timestamp_start, timestamp_end, job_id, machine_id):
    """ Creates fake activities for one machine between two timestamps"""
    time = timestamp_start
    activities = []
    while time <= timestamp_end:
        uptime_activity = Activity(machine_id=machine_id,
                                   timestamp_start=time,
                                   machine_state=MACHINE_STATE_RUNNING,
                                   activity_code_id=UPTIME_CODE_ID,
                                   job_id=job_id)
        time += randrange(400, 3000)
        uptime_activity.timestamp_end = time
        activities.append(uptime_activity)

        downtime_activity = Activity(machine_id=machine_id,
                                     timestamp_start=time,
                                     machine_state=MACHINE_STATE_OFF,
                                     activity_code_id=UNEXPLAINED_DOWNTIME_CODE_ID,
                                     job_id=job_id)
        time += randrange(60, 1000)
        downtime_activity.timestamp_end = time
        activities.append(downtime_activity)

    return activities



