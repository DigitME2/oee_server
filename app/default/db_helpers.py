import math as maths
from datetime import datetime, timedelta, date, time
from typing import List, Tuple

from flask import current_app

from app.default.models import Activity, Machine, Job, ProductionQuantity, InputDevice
from app.extensions import db
from config import Config

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


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


def get_machine_activities(machine: Machine, time_start: datetime, time_end: datetime, activity_code_id=None,
                           machine_state=None):
    """ Returns the activities for a machine, between two times. Activities can overrun the two times given"""

    if machine is None:
        current_app.logger.warn(f"Activities requested for non-existent Machine ID {machine}")
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


def get_jobs(time_start: datetime, time_end: datetime, machine: Machine = None):
    """ Get the jobs between two times and apply filters if required"""
    jobs_query = Job.query.filter(Job.end_time >= time_start).filter(Job.start_time <= time_end)
    if machine:
        jobs_query = jobs_query.filter(Job.machine_id == machine.id)
    jobs = jobs_query.all()
    # If required, add the current job (The above query will not get it)
    if machine.active_job and machine.active_job.start_time <= time_end:
        jobs.append(machine.active_job)
    return jobs


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
    good_amounts = {}
    reject_amounts = {}
    machines = Machine.query.all()
    for machine in machines:
        quantity_good = 0
        quantity_rejects = 0
        today_quantities = ProductionQuantity.query. \
            filter(ProductionQuantity.machine_id == machine.id). \
            filter(ProductionQuantity.time_start >= last_midnight). \
            filter(ProductionQuantity.time_end <= next_midnight).all()
        for q in today_quantities:
            quantity_good += q.quantity_good
            quantity_rejects += q.quantity_rejects
        good_amounts[machine.id] = quantity_good
        reject_amounts[machine.id] = quantity_rejects
    return good_amounts, reject_amounts


def add_new_input_device(uuid):
    """ Add a new input device from its UUID, and auto assign a machine """
    machines = Machine.query.all()
    unassigned_machines = [m for m in machines if m.input_device is None]
    if len(unassigned_machines) > 0:
        auto_assigned_machine_id = unassigned_machines[0].id
    else:
        auto_assigned_machine_id = None

    new_input = InputDevice(uuid=uuid, name=uuid, machine_id=auto_assigned_machine_id)
    db.session.add(new_input)
    db.session.flush()
    new_input.name = "Tablet " + str(new_input.id)
    db.session.commit()
    return new_input
