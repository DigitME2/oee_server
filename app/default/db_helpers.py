import logging
import math as maths
from datetime import datetime, timedelta, date, time
from operator import attrgetter
from random import randrange
from typing import List

from flask import current_app
from sqlalchemy import func

from app.default.models import Activity, Machine, ScheduledActivity, Settings, Job
from app.extensions import db
from config import Config


def complete_last_activity(machine_id, time_end: datetime = None, activity_code_id=None, commit=True):
    """ Gets the most recent active activity for a machine and then ends it with the current time, or a provided time.
    If an activity_code_id is provided, the activity will be updated with this code"""

    if time_end is None:
        time_end = datetime.now()
    # Get the last activity
    last_activity_id = get_current_machine_activity_id(machine_id)
    if last_activity_id is None:
        return
    last_activity = db.session.query(Activity).get(last_activity_id)
    last_activity.time_end = time_end
    # If an activity code is provided, edit the last activity to have that code
    if activity_code_id:
        last_activity.activity_code_id = activity_code_id
    if commit:
        db.session.commit()
    current_app.logger.debug(f"Ended {last_activity}")


def get_current_machine_activity_id(target_machine_id):
    """ Get the current activity of a machine by grabbing the most recent entry without an end time"""
    # Get all activities without an end time
    # The line below is causing a sql.programmingerror and im not sure why
    activities = Activity.query.filter(Activity.machine_id == target_machine_id, Activity.time_end == None).all()

    if len(activities) == 0:
        return None

    elif len(activities) == 1:
        return activities[0].id

    else:
        # If there is more than one activity without an end time, end them and return the most recent

        # Get the current activity by grabbing the one with the most recent start time
        current_activity = max(activities, key=lambda activity: activity.time_start)
        activities.remove(current_activity)

        current_app.logger.warning("More than one open-ended activity when trying to get current activity:")
        for act in activities:
            if act.time_end is None:
                current_app.logger.warning(f"Closing lost activity {act}")
                act.time_end = act.time_start
                db.session.add(act)
                db.session.commit()

        return current_activity.id


def get_current_machine_schedule_activity_id(target_machine_id):
    """ Get the current scheduled activity of a machine by grabbing the most recent entry without an end time"""
    # Get all activities without an end time
    # The line below is causing a sql.programmingerror and im not sure why
    activities = ScheduledActivity.query.filter(ScheduledActivity.machine_id == target_machine_id,
                                                ScheduledActivity.time_end == None).all()

    if len(activities) == 0:
        current_app.logger.debug(f"No current scheduled activity on machine ID {target_machine_id}")
        return None

    elif len(activities) == 1:
        current_app.logger.debug(f"Current scheduled activity for machine ID {target_machine_id} -> {activities[0]}")
        return activities[0].id


def get_current_user_activity_id(target_user_id):
    """ Get the current activity of a user by grabbing the most recent entry without an end time"""
    # Get all activities without an end time
    # The line below is causing a sql.programmingerror and im not sure why
    activities = Activity.query.filter(Activity.user_id == target_user_id, Activity.time_end == None).all()

    if len(activities) == 0:
        current_app.logger.debug(f"No current activity on user ID {target_user_id}")
        return None

    elif len(activities) == 1:
        current_app.logger.debug(f"Current activity for user ID {target_user_id} -> {activities[0]}")
        return activities[0].id

    else:
        # If there is more than one activity without an end time, end them and return the most recent

        # Get the current activity by grabbing the one with the most recent start time
        current_activity = max(activities, key=lambda activity: activity.time_start)
        activities.remove(current_activity)

        current_app.logger.warning("More than one open-ended activity when trying to get current activity:")
        for act in activities:
            if act.time_end is None:
                current_app.logger.warning(f"Closing lost activity {act}")
                act.time_end = act.time_start
                db.session.add(act)
                db.session.commit()

        return current_activity.id


def flag_activities(activities: List[Activity], threshold):
    """ Filters a list of activities, adding explanation_required=True to those that require an explanation
    for downtime above a defined threshold"""
    ud_index_counter = 0
    downtime_explanation_threshold = timedelta(seconds=threshold)
    for act in activities:
        # Only Flag activities with the downtime code and with a duration longer than the threshold
        if act.activity_code_id == Config.UNEXPLAINED_DOWNTIME_CODE_ID and \
                (act.time_end - act.time_start) > downtime_explanation_threshold:
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
        split_time = datetime.now()

    # Copy the old activity to a new activity
    new_activity = Activity(machine_id=old_activity.machine_id,
                            machine_state=old_activity.machine_state,
                            explanation_required=old_activity.explanation_required,
                            time_start=split_time,
                            activity_code_id=old_activity.activity_code_id,
                            job_id=old_activity.job_id)

    # End the old activity
    old_activity.time_end = split_time

    db.session.add(new_activity)
    db.session.commit()
    current_app.logger.debug(f"Ended {old_activity}")
    current_app.logger.debug(f"Started {new_activity}")


def get_dummy_machine_activity(time_start: datetime, time_end: datetime, job_id, machine_id):
    """ Creates fake activities for one machine between two times"""
    virtual_time = time_start
    activities = []
    while virtual_time <= time_end:
        uptime_activity = Activity(machine_id=machine_id,
                                   time_start=virtual_time,
                                   machine_state=Config.MACHINE_STATE_RUNNING,
                                   activity_code_id=Config.UPTIME_CODE_ID,
                                   job_id=job_id)
        virtual_time += randrange(400, 3000)
        uptime_activity.time_end = virtual_time
        activities.append(uptime_activity)

        downtime_activity = Activity(machine_id=machine_id,
                                     time_start=virtual_time,
                                     machine_state=Config.MACHINE_STATE_OFF,
                                     activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                                     job_id=job_id)
        virtual_time += randrange(60, 1000)
        downtime_activity.time_end = virtual_time
        activities.append(downtime_activity)

    return activities


def get_legible_duration(time_start: datetime, time_end: datetime):
    """ Takes two times and returns a string in the format <hh:mm> <x> minutes"""
    minutes = maths.floor((time_end - time_start).total_seconds() / 60)
    hours = maths.floor((time_end - time_start).total_seconds() / 3600)
    if minutes == 0:
        return f"{maths.floor((time_end - time_start).total_seconds())} seconds"
    if hours == 0:
        return f"{minutes} minutes"
    else:
        leftover_minutes = minutes - (hours * 60)
        return f"{hours} hours {leftover_minutes} minutes"


def get_machine_activities(machine_id, time_start: datetime, time_end: datetime):
    """ Returns the activities for a machine, between two times"""

    machine = Machine.query.get(machine_id)
    if machine is None:
        current_app.logger.warn(f"Activities requested for non-existent Machine ID {machine_id}")
        return
    activities = Activity.query \
        .filter(Activity.machine_id == machine.id) \
        .filter(Activity.time_end >= time_start) \
        .filter(Activity.time_start <= time_end).all()
    # If required, add the current_activity (The above loop will not get it)
    # and extend the end time to the end of the requested time

    current_activity_id = get_current_machine_activity_id(target_machine_id=machine.id)
    if current_activity_id is not None:
        current_act = Activity.query.get(current_activity_id)
        # Don't add the current activity if it started after the requested end of the graph
        if current_act.time_start <= time_end:
            activities.append(current_act)

    return activities


def get_machine_scheduled_activities(machine_id, time_start: datetime, time_end: datetime):
    """ Returns scheduled activities for a machine between two times"""
    activities = ScheduledActivity.query \
        .filter(ScheduledActivity.machine_id == machine_id) \
        .filter(ScheduledActivity.time_end >= time_start) \
        .filter(ScheduledActivity.time_start <= time_end).all()
    return activities


def get_user_activities(user_id, time_start: datetime, time_end: datetime):
    """ Returns the activities for a user, between two times"""

    activities = Activity.query \
        .filter(Activity.user_id == user_id) \
        .filter(Activity.time_end >= time_start) \
        .filter(Activity.time_start <= time_end).all()

    # If required, add the current_activity (The above loop will not get it)
    current_activity_id = get_current_user_activity_id(target_user_id=user_id)
    if current_activity_id is not None:
        current_act = Activity.query.get(current_activity_id)
        # Don't add the current activity if it started after the requested end
        if current_act.time_start <= time_end:
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


def machine_schedule_active(machine, dt: datetime = None):
    """ Return true if the machine is scheduled to be running at a specific time (or now, if not specified)"""
    if not machine.schedule:
        logging.warning(f"No schedule for machine {machine.id}")
        return False
    if not dt:
        dt = datetime.now()
    # Get the shift for this day of the week
    shift = machine.schedule.get_shifts().get(dt.weekday())
    shift_start = datetime.combine(dt, datetime.strptime(shift[0], "%H%M").timetz())
    shift_end = datetime.combine(dt, datetime.strptime(shift[1], "%H%M").timetz())
    if shift_start < dt < shift_end:
        return True
    else:
        return False


def backfill_missed_schedules():
    last_schedule_time = db.session.query(func.max(ScheduledActivity.time_start)).first()[0]
    if last_schedule_time is not None:
        start_date = last_schedule_time.date()
    else:
        start_date = Settings.query.get(1).first_start.date()
    no_of_days_to_backfill = (datetime.now().date() - start_date).days
    if no_of_days_to_backfill <= 0:
        return
    dates = [datetime.now().date() - timedelta(days=x) for x in range(0, no_of_days_to_backfill + 1)]
    for d in dates:
        create_all_scheduled_activities(create_date=d)


def create_day_scheduled_activities(machine: Machine, shift_start, shift_end, create_date: date = None):
    """ Create a day's scheduled activity for a single machine"""
    if not create_date:
        create_date = datetime.now().date()

    current_app.logger.info(f"Creating Scheduled Activities for {create_date.strftime('%d-%m-%y')}")
    last_midnight = datetime.combine(date=create_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    next_midnight = last_midnight + timedelta(days=1)

    # Check to see if any scheduled activities already exist for today and skip if any exist
    existing_activities = ScheduledActivity.query \
        .filter(ScheduledActivity.machine_id == machine.id) \
        .filter(ScheduledActivity.time_start >= last_midnight) \
        .filter(ScheduledActivity.time_end <= next_midnight).all()
    if len(existing_activities) > 0:
        current_app.logger.info(f"Scheduled activities already exist on {create_date} for {machine} Skipping...")
        return

    if shift_start != last_midnight:  # Skip making this activity if it will be 0 length
        before_shift = ScheduledActivity(machine_id=machine.id,
                                         scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                         time_start=last_midnight,
                                         time_end=shift_start)
        db.session.add(before_shift)

    if shift_start != shift_end:  # Skip making this activity if it will be 0 length
        during_shift = ScheduledActivity(machine_id=machine.id,
                                         scheduled_machine_state=Config.MACHINE_STATE_RUNNING,
                                         time_start=shift_start,
                                         time_end=shift_end)
        db.session.add(during_shift)

    if shift_end != next_midnight:  # Skip making this activity if it will be 0 length
        after_shift = ScheduledActivity(machine_id=machine.id,
                                        scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                        time_start=shift_end,
                                        time_end=next_midnight)
        db.session.add(after_shift)

    db.session.commit()


def create_all_scheduled_activities(create_date: date = None):
    """ Create all the scheduled activities on a date"""
    if not create_date:
        create_date = datetime.now().date()

    current_app.logger.info(f"Creating Scheduled Activities for {create_date.strftime('%d-%m-%y')}")
    last_midnight = datetime.combine(date=create_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    next_midnight = last_midnight + timedelta(days=1)

    for machine in Machine.query.all():
        if not machine.schedule:
            logging.warning(f"No schedule for machine {machine.id}")
            continue

        # Check to see if any scheduled activities already exist for today and skip if any exist
        existing_activities = ScheduledActivity.query \
            .filter(ScheduledActivity.machine_id == machine.id) \
            .filter(ScheduledActivity.time_start >= last_midnight) \
            .filter(ScheduledActivity.time_end <= next_midnight).all()
        if len(existing_activities) > 0:
            current_app.logger.info(f"Scheduled activities already exist today for {machine} Skipping...")
            continue

        # Get the shift for this day of the week
        weekday = create_date.weekday()
        shift = machine.schedule.get_shifts().get(weekday)

        # Create datetime objects with today's date and the times from the schedule table
        shift_start = datetime.combine(create_date, datetime.strptime(shift[0], "%H%M").timetz())
        shift_end = datetime.combine(create_date, datetime.strptime(shift[1], "%H%M").timetz())

        if shift_start != last_midnight:  # Skip making this activity if it will be 0 length
            before_shift = ScheduledActivity(machine_id=machine.id,
                                             scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                             time_start=last_midnight,
                                             time_end=shift_start)
            db.session.add(before_shift)

        if shift_start != shift_end:  # Skip making this activity if it will be 0 length
            during_shift = ScheduledActivity(machine_id=machine.id,
                                             scheduled_machine_state=Config.MACHINE_STATE_RUNNING,
                                             time_start=shift_start,
                                             time_end=shift_end)
            db.session.add(during_shift)

        if shift_end != next_midnight:  # Skip making this activity if it will be 0 length
            after_shift = ScheduledActivity(machine_id=machine.id,
                                            scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                            time_start=shift_end,
                                            time_end=next_midnight)
            db.session.add(after_shift)

        db.session.commit()


def get_activity_cropped_start_end(act: Activity,
                                   requested_start: datetime,
                                   requested_end: datetime) -> (datetime, datetime):
    """ Crops the start and end of an activity if it overruns the requested start or end time."""
    if act.time_start is not None and act.time_start > requested_start:
        start = act.time_start
    else:
        start = requested_start

        # If the activity extends past the requested end or has no end, crop it to the requested end (or current time)
    if act.time_end is None or act.time_end > requested_end:
        end = min([requested_end, datetime.now()])
    else:
        end = act.time_end
    return start, end


def get_job_cropped_start_end_ratio(job: Job,
                                    requested_start: datetime,
                                    requested_end: datetime) -> (datetime, datetime, float):
    """ Crops the start and end of a job if it overruns the requested start or end time. Also returns the
    ratio of time cropped to total time"""
    if job.start_time is not None and job.start_time > requested_start:
        start = job.start_time
    else:
        start = requested_start

    # If the job extends past the requested end or has no end, crop it to the requested end (or current time)
    if job.end_time is None or job.end_time > requested_end:
        end = min([requested_end, datetime.now()])
    else:
        end = job.end_time
    job_length = (job.end_time - job.start_time).total_seconds()
    cropped_length = (end - start).total_seconds()
    ratio_of_length_used = cropped_length / job_length
    return start, end, ratio_of_length_used
