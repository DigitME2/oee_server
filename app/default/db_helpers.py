import math as maths
from datetime import datetime
from operator import attrgetter
from random import randrange
from time import time

from flask import current_app

from app import db
from app.default.models import Activity, Machine
from config import Config


def complete_last_activity(machine_id, timestamp_end=None, activity_code_id=None,):
    """ Gets the most recent active activity for a machine and then ends it with the current time, or a provided time.
    If an activity_code_id is provided, the activity will be updated with this code"""

    # Warning to future Sam, don't put datetime.now() as the default argument, it will break this function
    if timestamp_end is None:
        timestamp_end = datetime.now().timestamp()
    # Get the last activity
    last_activity_id = get_current_machine_activity_id(machine_id)
    if last_activity_id is None:
        return
    last_activity = db.session.query(Activity).get(last_activity_id)
    last_activity.timestamp_end = timestamp_end
    # If an activity code is provided, edit the last activity to have that code
    if activity_code_id:
        last_activity.activity_code_id = activity_code_id
    db.session.commit()
    current_app.logger.debug(f"Ended {last_activity}")


def get_current_machine_activity_id(target_machine_id):
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
            if act.timestamp_end is None:
                current_app.logger.warning(f"Closing lost activity {act}")
                act.timestamp_end = act.timestamp_start
                db.session.add(act)
                db.session.commit()

        return current_activity.id


def get_current_user_activity_id(target_user_id):
    """ Get the current activity of a user by grabbing the most recent entry without an end timestamp"""
    # Get all activities without an end time
    # The line below is causing a sql.programmingerror and im not sure why
    activities = Activity.query.filter(Activity.user_id == target_user_id, Activity.timestamp_end == None).all()

    if len(activities) == 0:
        current_app.logger.debug(f"No current activity on user ID {target_user_id}")
        return None

    elif len(activities) == 1:
        current_app.logger.debug(f"Current activity for user ID {target_user_id} -> {activities[0]}")
        return activities[0].id

    else:
        # If there is more than one activity without an end time, end them and return the most recent

        # Get the current activity by grabbing the one with the most recent start time
        current_activity = max(activities, key=lambda activity: activity.timestamp_start)
        activities.remove(current_activity)

        current_app.logger.warning("More than one open-ended activity when trying to get current activity:")
        for act in activities:
            if act.timestamp_end is None:
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


def get_machine_activities(machine_id, timestamp_start, timestamp_end):
    """ Returns the activities for a machine, between two times"""

    machine = Machine.query.get(machine_id)
    if machine is None:
        current_app.logger.warn(f"Activities requested for non-existent Machine ID {machine_id}")
        return
    activities = Activity.query \
        .filter(Activity.machine_id == machine.id) \
        .filter(Activity.timestamp_end >= timestamp_start) \
        .filter(Activity.timestamp_start <= timestamp_end).all()
    # If required, add the current_activity (The above loop will not get it)
    # and extend the end time to the end of the requested time

    current_activity_id = get_current_machine_activity_id(target_machine_id=machine.id)
    if current_activity_id is not None:
        current_act = Activity.query.get(current_activity_id)
        # Don't add the current activity if it started after the requested end of the graph
        if current_act.timestamp_start <= timestamp_end:
            activities.append(current_act)

    return activities


def get_user_activities(user_id, timestamp_start, timestamp_end):
    """ Returns the activities for a user, between two times"""

    activities = Activity.query \
        .filter(Activity.user_id == user_id) \
        .filter(Activity.timestamp_end >= timestamp_start) \
        .filter(Activity.timestamp_start <= timestamp_end).all()

    # If required, add the current_activity (The above loop will not get it)
    current_activity_id = get_current_user_activity_id(target_user_id=user_id)
    if current_activity_id is not None:
        current_act = Activity.query.get(current_activity_id)
        # Don't add the current activity if it started after the requested end
        if current_act.timestamp_start <= timestamp_end:
            activities.append(current_act)

    return activities


def get_assigned_machine(device_ip):
    """ Get the machine assigned to a device (using its ip)"""
    assigned_machines = Machine.query.filter_by(device_ip=device_ip, active=True).all()
    # If no or multiple machines are assigned, show an error message
    if len(assigned_machines) == 0:
        current_app.logger.info(f"No machine assigned to {device_ip}")
        return None
    elif len(assigned_machines) > 1:
        current_app.logger.info(f"Multiple machines assigned to {device_ip}")
    else:
        return assigned_machines[0]


def get_machines_last_job(machine_id):
    """ Get the last (completed) job a machine ran"""
    machine = Machine.query.get(machine_id)
    jobs = [j for j in machine.jobs if j.end_time is not None]
    if len(jobs) == 0:
        return None
    most_recent_job = max(jobs, key=attrgetter('end_time'))
    return most_recent_job



