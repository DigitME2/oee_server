import logging
import math as maths
from datetime import datetime, timedelta, date, time
from operator import attrgetter
from typing import List, Tuple

from flask import current_app
from sqlalchemy import func

from app.default.models import Activity, Machine, ScheduledActivity, Settings, Job, ProductionQuantity
from app.extensions import db
from config import Config


def get_current_machine_schedule_activity_id(target_machine_id):
    """ Get the current scheduled activity of a machine by grabbing the most recent entry without an end time"""
    # Get all activities without an end time
    activities = ScheduledActivity.query.filter(ScheduledActivity.machine_id == target_machine_id,
                                                ScheduledActivity.time_end == None).all()

    if len(activities) == 0:
        current_app.logger.debug(f"No current scheduled activity on machine ID {target_machine_id}")
        return None

    elif len(activities) == 1:
        current_app.logger.debug(f"Current scheduled activity for machine ID {target_machine_id} -> {activities[0]}")
        return activities[0].id


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


def get_machine_activities(machine_id, time_start: datetime, time_end: datetime, activity_code_id=None,
                           machine_state=None):
    """ Returns the activities for a machine, between two times. Activities can overrun the two times given"""

    machine = Machine.query.get(machine_id)
    if machine is None:
        current_app.logger.warn(f"Activities requested for non-existent Machine ID {machine_id}")
        return
    activities_query = Activity.query \
        .filter(Activity.machine_id == machine.id) \
        .filter(Activity.time_end >= time_start) \
        .filter(Activity.time_start <= time_end)
    if activity_code_id:
        activities_query = activities_query.filter(Activity.activity_code_id == activity_code_id)
    if machine_state:
        activities_query = activities_query.filter(Activity.machine_state == machine_state)
    activities = activities_query.all()
    # If required, add the current_activity (The above loop will not get it)
    if machine.current_activity.time_start <= time_end:
        # Only add the current activity if it matches the filters given to this function
        if not activity_code_id or machine.current_activity.activity_code_id == activity_code_id:
            if not machine_state or machine.current_activity.machine_state == machine_state:
                activities.append(machine.current_activity)
    return activities


def get_machine_jobs(machine_id, time_start: datetime, time_end: datetime):
    """ Get the jobs of a machine between two times"""
    jobs = Job.query \
        .filter(Job.end_time >= time_start) \
        .filter(Job.start_time <= time_end) \
        .filter(Job.machine_id == machine_id).all()
    machine = Machine.query.get(machine_id)
    # If required, add the current job (The above query will not get it)
    if machine.active_job and machine.active_job.start_time <= time_end:
        jobs.append(machine.active_job)
    return jobs

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

    # Add any unfinished activities (The above call will not get them)
    active_activities = Activity.query.filter(Activity.user_id == user_id, Activity.time_end == None).all()
    for aa in active_activities:
        if aa.time_start <= time_end:
            activities.append(aa)
    return activities


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
    """ Crops the start and end of an activity if it overruns the requested start or end time.
    e.g. if an activity is from 2pm -> 4pm and the requested start/end is 1pm -> 3pm, this function will return
    2pm -> 3pm. """
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
    job_length = (end - start).total_seconds()
    cropped_length = (end - start).total_seconds()
    ratio_of_length_used = cropped_length / job_length
    return start, end, ratio_of_length_used


def get_daily_production_dict(requested_date: date = None) -> Tuple[dict, dict]:
    if requested_date is None:
        requested_date = datetime.now().date()
    last_midnight = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    next_midnight = last_midnight + timedelta(days=1)
    production_amounts = {}
    reject_amounts = {}
    machines = Machine.query.all()
    for machine in machines:
        quantity_produced = 0
        quantity_rejects = 0
        today_quantities = ProductionQuantity.query. \
            filter(ProductionQuantity.machine_id == machine.id). \
            filter(ProductionQuantity.time >= last_midnight). \
            filter(ProductionQuantity.time <= next_midnight).all()
        for q in today_quantities:
            quantity_produced += q.quantity_produced
            quantity_rejects += q.quantity_rejects
        production_amounts[machine.id] = quantity_produced
        reject_amounts[machine.id] = quantity_rejects
    return production_amounts, reject_amounts
