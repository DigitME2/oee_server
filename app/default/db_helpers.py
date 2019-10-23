import math as maths
from datetime import datetime, timedelta
from random import randrange
from time import time

from flask import current_app

from app import db
from app.default.models import Activity, Machine, ScheduledActivity
from config import Config


def complete_last_activity(machine_id, timestamp_end=None):
    """ Gets the most recent active activity for a machine and then ends it with the current time, or a provided time"""

    # Don't put datetime.now() as the default argument, it will break this function
    if timestamp_end is None:
        timestamp_end = datetime.now().timestamp()
    last_activity_id = get_current_activity_id(machine_id)
    if last_activity_id is None:
        return
    last_activity = db.session.query(Activity).get(last_activity_id)
    last_activity.timestamp_end = timestamp_end
    db.session.commit()
    current_app.logger.debug(f"Ended {last_activity}")


def get_current_activity_id(target_machine_id):
    """ Get the current activity of a machine by grabbing the most recent entry without an end timestamp"""
    # Get all activities without an end time
    # The line below is causing a sql.programmingerror and im not sure why
    activities = Activity.query.filter(Activity.machine_id == target_machine_id, Activity.timestamp_end == None).all()

    if len(activities) == 0:
        current_app.logger.debug(f"No current activity on machine ID {target_machine_id}")
        return None

    elif len(activities) == 1:
        current_app.logger.debug(f"Current activity for machine ID {target_machine_id} -> {activities[0]}")
        return activities[0].id

    else:
        # If there is more than one activity without an end time, end them and return the most recent

        # Get the current activity by grabbing the one with the most recent start time
        current_activity = max(activities, key=lambda activity: activity.timestamp_start)
        activities.remove(current_activity)

        current_app.logger.warning("More than one open-ended activity when trying to get current activity:")
        for act in activities:
            if act.timestamp_end == None:
                current_app.logger.warning(f"Closing lost activity {act}")
                act.timestamp_end = act.timestamp_start
                db.session.add(act)
                db.session.commit()

        return current_activity.id


def flag_activities(activities, threshold):
    """ Filters a list of activities, adding explanation_required=True to those that require an explanation
    for downtime above a defined threshold"""
    ud_index_counter = 0
    downtime_explanation_threshold_s = threshold
    for act in activities:
        # Only Flag activities with the downtime code and with a duration longer than the threshold
        if act.activity_code_id == Config.UNEXPLAINED_DOWNTIME_CODE_ID and \
                (act.timestamp_end - act.timestamp_start) > downtime_explanation_threshold_s:
            act.explanation_required = True
            # Give the unexplained downtimes their own index
            act.ud_index = ud_index_counter
            ud_index_counter += 1
        else:
            act.explanation_required = False
    db.session.commit()
    db.session.close()
    return activities


def split_activity(activity_id, split_time=None):
    """ Ends an activity and starts a new activity with the same values, ending/starting at the split_time"""
    old_activity = Activity.query.get(activity_id)

    if split_time is None:
        split_time = time()

    # Copy the old activity to a new activity
    new_activity = Activity(machine_id=old_activity.machine_id,
                            machine_state=old_activity.machine_state,
                            explanation_required=old_activity.explanation_required,
                            timestamp_start=split_time,
                            activity_code_id=old_activity.activity_code_id,
                            job_id=old_activity.job_id)

    # End the old activity
    old_activity.timestamp_end = split_time

    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.debug(f"Ended {old_activity}")
    current_app.logger.debug(f"Started {new_activity}")


def get_dummy_machine_activity(timestamp_start, timestamp_end, job_id, machine_id):
    """ Creates fake activities for one machine between two timestamps"""
    virtual_time = timestamp_start
    activities = []
    while virtual_time <= timestamp_end:
        uptime_activity = Activity(machine_id=machine_id,
                                   timestamp_start=virtual_time,
                                   machine_state=Config.MACHINE_STATE_RUNNING,
                                   activity_code_id=Config.UPTIME_CODE_ID,
                                   job_id=job_id)
        virtual_time += randrange(400, 3000)
        uptime_activity.timestamp_end = virtual_time
        activities.append(uptime_activity)

        downtime_activity = Activity(machine_id=machine_id,
                                     timestamp_start=virtual_time,
                                     machine_state=Config.MACHINE_STATE_OFF,
                                     activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                                     job_id=job_id)
        virtual_time += randrange(60, 1000)
        downtime_activity.timestamp_end = virtual_time
        activities.append(downtime_activity)

    return activities


def decimal_time_to_current_day(decimal_time):
    """ Turns decimal time for an hour (ie 9.5=9.30am) into a timestamp for the given time on the current day"""
    hour = maths.floor(decimal_time)
    minute = (decimal_time - hour) * 60
    return datetime.now().replace(hour=hour, minute=minute).timestamp()


def get_activity_duration(activity_id):
    """ Gets the duration of an activity in minutes"""
    act = Activity.query.get(activity_id)
    start = act.timestamp_start
    if act.timestamp_end is not None:
        end = act.timestamp_end
    else:
        end = datetime.now().timestamp()
    return (end - start)/60


def get_legible_duration(timestamp_start, timestamp_end):
    """ Takes two timestamps and returns a string in the format <hh:mm> <x> minutes"""
    minutes = maths.floor((timestamp_end - timestamp_start) / 60)
    hours = maths.floor((timestamp_end - timestamp_start) / 3600)
    if minutes == 0:
        return f"{maths.floor(timestamp_end - timestamp_start)} seconds"
    if hours == 0:
        return f"{minutes} minutes"
    else:
        leftover_minutes = minutes - (hours * 60)
        return f"{hours} hours {leftover_minutes} minutes"

