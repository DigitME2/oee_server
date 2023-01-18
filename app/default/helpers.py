import math as maths
from datetime import datetime, timedelta, time
from typing import List, Union

from flask import current_app, flash, abort

from app.default.models import Activity, Machine, Job, ProductionQuantity, InputDevice, SHIFT_STRFTIME_FORMAT, \
    ShiftPeriod, ActivityCode
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
                (act.end_time - act.start_time) > downtime_explanation_threshold:
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
                            explanation_required=old_activity.explanation_required,
                            time_start=split_time,
                            activity_code_id=old_activity.activity_code_id,
                            job_id=old_activity.job_id)

    # End the old activity
    old_activity.end_time = split_time

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
                           machine_state=None, scheduled_state=None) -> List[Activity]:
    """ Returns the activities for a machine, between two times. Activities can overrun the two times given"""

    if machine is None:
        current_app.logger.warn(f"Activities requested for non-existent Machine ID {machine}")
        return
    activities_query = Activity.query \
        .filter(Activity.machine_id == machine.id) \
        .filter(Activity.end_time >= time_start) \
        .filter(Activity.start_time <= time_end)
    if activity_code_id:
        activities_query = activities_query.filter(Activity.activity_code_id == activity_code_id)
    if machine_state:
        activity_codes = ActivityCode.query.filter_by(machine_state=machine_state).all()
        for ac in activity_codes:
            activities_query = activities_query.filter(Activity.activity_code_id == ac.id)
    activities = activities_query.all()
    # If required, add the current_activity (The above loop will not get it)
    if machine.current_activity and machine.current_activity.start_time <= time_end:
        # Only add the current activity if it matches the filters given to this function
        if not activity_code_id or machine.current_activity.activity_code_id == activity_code_id:
            if not machine_state or machine.current_activity.activity_code.machine_state == machine_state:
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
        .filter(Activity.end_time >= time_start) \
        .filter(Activity.start_time <= time_end).all()

    # Add any unfinished activities (The above call will not get them)
    active_activities = Activity.query.filter(Activity.user_id == user_id, Activity.end_time == None).all()
    for aa in active_activities:
        if aa.start_time <= time_end:
            activities.append(aa)
    return activities


def get_cropped_start_end_ratio(obj: Union[Job, ProductionQuantity, Activity],
                                requested_start: datetime,
                                requested_end: datetime) -> (datetime, datetime, float):
    """ Crops the start and end of a job/activity/production_quantity if it overruns the requested start or end time.
    Also returns the ratio of time cropped to total time"""
    if obj.start_time and obj.start_time > requested_start:
        cropped_start = obj.start_time
    else:
        cropped_start = requested_start

    # If the job extends past the requested end or has no end, crop it to the requested end (or current time)
    if obj.end_time is None or obj.end_time > requested_end:
        cropped_end = min([requested_end, datetime.now()])
    else:
        cropped_end = obj.end_time
    if not obj.end_time:
        job_length = (datetime.now() - obj.start_time).total_seconds()
    else:
        job_length = (obj.end_time - obj.start_time).total_seconds()
    cropped_length = (cropped_end - cropped_start).total_seconds()
    if job_length == 0:
        ratio_of_length_used = 1
    else:
        ratio_of_length_used = cropped_length / job_length
    return cropped_start, cropped_end, ratio_of_length_used


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


def get_current_machine_shift_period(machine: Machine) -> ShiftPeriod:
    day = datetime.now().strftime("%A")[0:3].lower()  # day of the week in the format mon, tue etc
    time_now = datetime.now().time()
    # Get a list of today's shifts that have already passed
    today_past_shifts = []
    for p in machine.shift.shift_periods:
        if p.day == day:
            shift_start_time = datetime.strptime(p.start_time, SHIFT_STRFTIME_FORMAT).time()
            if shift_start_time < time_now:
                today_past_shifts.append(p)
    # The most recent of today's past shifts is the current shift
    today_past_shifts.sort(key=lambda x: float(x.start_time), reverse=True)
    current_shift_period = today_past_shifts[0]
    return current_shift_period


def get_machine_activity_duration(machine: Machine, time_start: datetime, time_end: datetime, machine_state: int = None,
                                  activity_code_id: int = None):
    """ Calculate the amount of time a machine spent in a certain state between two times"""
    activities = get_machine_activities(machine, time_start, time_end, activity_code_id=activity_code_id,
                                        machine_state=machine_state)
    duration = 0
    for act in activities:
        start, end, _ = get_cropped_start_end_ratio(act, time_start, time_end)
        duration += (end - start).total_seconds()
    return duration


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
