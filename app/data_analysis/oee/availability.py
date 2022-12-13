import logging
from datetime import datetime, timedelta, date, time

import humanize as humanize
from flask import current_app

from app.default.db_helpers import get_user_activities, get_machine_activities, get_activity_cropped_start_end, \
    get_machine_scheduled_activities
from app.default.models import Activity, ActivityCode, ScheduledActivity, Machine
from app.login.models import User
from config import Config


def get_machine_availability(machine: Machine, time_start: datetime, time_end: datetime):
    """ Takes a machine id and two times, and returns the machine's availability (0-1) for calculating OEE"""
    runtime = get_machine_runtime(machine, time_start, time_end)
    schedule_dict = get_schedule_dict(machine, time_start, time_end, units="seconds")
    scheduled_uptime = schedule_dict["Scheduled Run Time"]
    scheduled_downtime = schedule_dict["Scheduled Down Time"]
    if scheduled_uptime and scheduled_downtime == 0:
        current_app.logger(f"OEE Calculation for machine {machine.name} performed between {time_start} and {time_end} "
                           f"has no scheduled activities. Assuming 100% scheduled uptime")
        scheduled_uptime = (time_end - time_start).total_seconds()
    try:
        availability = runtime / scheduled_uptime
    except ZeroDivisionError:
        return 1
    if availability > 1:
        logging.warning(f"Availability of >1 calculated for machine {machine.name} on {time_start.date()}")
    return availability


def get_daily_machine_availability_dict(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's availability on the given date """
    if not requested_date:
        requested_date = datetime.now().date()
    # Use 00:00 and 24:00 on the selected day
    period_start = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    period_end = period_start + timedelta(days=1)
    # If the end is in the future, change to now
    if period_end > datetime.now():
        period_end = datetime.now()
    availability_dict = {}
    for machine in Machine.query.all():
        availability_dict[machine.id] = get_machine_availability(machine, period_start, period_end)
    if human_readable:
        for k, v in availability_dict.items():
            v = v * 100
            availability_dict[k] = f"{round(v, 1)}%"
    return availability_dict


def get_machine_runtime(machine: Machine, requested_start: datetime, requested_end: datetime):
    """ Takes a machine id and two times, and returns the amount of time the machine was running """
    # Get all the activities for the machine between the two given times, where the machine is up
    activities = get_machine_activities(machine, time_start=requested_start, time_end=requested_end,
                                        machine_state=Config.MACHINE_STATE_RUNNING)
    run_time = 0
    for act in activities:
        start, end = get_activity_cropped_start_end(act, requested_start, requested_end)
        run_time += (end - start).total_seconds()
    return run_time


def get_scheduled_machine_runtime(machine: Machine, requested_start: datetime, requested_end: datetime):
    """ Takes a machine id and two times, and returns the amount of time the machine was scheduled to run"""
    # Get all the activities for the machine between the two given times, where the machine is up
    activities = get_machine_scheduled_activities(machine.id, time_start=requested_start, time_end=requested_end,
                                                  machine_state=Config.MACHINE_STATE_RUNNING)
    run_time = 0
    for act in activities:
        start, end = get_activity_cropped_start_end(act, requested_start, requested_end)
        run_time += (end - start).total_seconds()
    return run_time


def get_activity_duration_dict(requested_start: datetime, requested_end: datetime, machine: Machine = None,
                               user: User = None, use_description_as_key=False, units="seconds", human_readable=False):
    """ Returns a dict containing the total duration of each activity_code between two times in the format:
    activity_code_id: duration(seconds) e.g. 1: 600
    If the use_description_as_key is passed, the activity_code_id is replaced with its description e.g. uptime: 600"""

    if user:
        # Get all activities for a user
        activities = get_user_activities(user_id=user.id,
                                         time_start=requested_start,
                                         time_end=requested_end)
    elif machine:
        # Get all activities for a machine
        activities = get_machine_activities(machine=machine,
                                            time_start=requested_start,
                                            time_end=requested_end)
    else:
        # Get all activities
        activities = Activity.query \
            .filter(Activity.time_end >= requested_start) \
            .filter(Activity.time_start <= requested_end).all()

    # Initialise the dictionary that will hold the totals
    activities_dict = {}

    # Add all activity codes to the dictionary.
    act_codes = ActivityCode.query.all()
    for code in act_codes:
        key = code.short_description if use_description_as_key else code.id
        activities_dict[key] = 0

    for act in activities:
        start, end = get_activity_cropped_start_end(act, requested_start, requested_end)

        # Calculate the duration and add to the dict
        if act.activity_code is None:
            print("here")
        key = act.activity_code.short_description if use_description_as_key else act.activity_code_id
        activities_dict[key] += (end - start).total_seconds()

    if human_readable:
        for k, v in activities_dict.items():
            v = humanize.precisedelta(timedelta(seconds=v), minimum_unit="minutes", format="%0.1f")
            activities_dict[k] = v
    # Convert to minutes if requested
    elif units == "minutes":
        for n in activities_dict:
            activities_dict[n] = activities_dict[n] / 60
    return activities_dict


def get_daily_activity_duration_dict(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's activity dict on the given date """
    if not requested_date:
        requested_date = datetime.now().date()
    # Use 00:00 and 24:00 on the selected day
    period_start = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    period_end = period_start + timedelta(days=1)
    # If the end is in the future, change to now
    if period_end > datetime.now():
        period_end = datetime.now()
    activity_duration_dict = {}
    for machine in Machine.query.all():
        activity_duration_dict[machine.id] = get_activity_duration_dict(period_start, period_end, machine=machine,
                                                                        units="minutes", human_readable=human_readable)
    return activity_duration_dict


def get_daily_scheduled_runtime_dicts(requested_date: date = None, human_readable=False):
    """ Return a dictionary of schedule dicts returned by get_schedule_dict for every machine for a date"""
    if not requested_date:
        requested_date = datetime.now().date()
    # Use 00:00 and 24:00 on the selected day
    period_start = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    period_end = period_start + timedelta(days=1)
    # If the end is in the future, change to now
    if period_end > datetime.now():
        period_end = datetime.now()
    runtime_dict = {}
    for machine in Machine.query.all():
        scheduled_runtime = get_scheduled_machine_runtime(machine, period_start, period_end)
        if human_readable:
            runtime_dict[machine.id] = humanize.precisedelta(
                timedelta(seconds=scheduled_runtime), minimum_unit="minutes", format="%0.1f"
            )
        else:
            runtime_dict[machine.id] = scheduled_runtime
    return runtime_dict


def get_schedule_dict(machine, time_start: datetime, time_end: datetime, units="seconds"):
    """ Takes a machine id and two times, and returns a dict with:
    scheduled_run_time
    scheduled_down_time
    unscheduled_time"""
    # Get all the scheduled activities
    activities = ScheduledActivity.query \
        .filter(ScheduledActivity.machine_id == machine.id) \
        .filter(ScheduledActivity.time_end >= time_start) \
        .filter(ScheduledActivity.time_start <= time_end).all()
    total_time = time_end - time_start
    scheduled_run_time = timedelta()
    scheduled_down_time = timedelta()
    unscheduled_time = timedelta()
    for act in activities:
        # Skip if it's after the requested end
        if act.time_start > time_end:
            continue
        # If the activity extends past the  start or end, crop it short
        if act.time_start < time_start:
            temp_act_start = time_start
        else:
            temp_act_start = act.time_start
        if act.time_end > time_end:
            tem_act_end = time_end
        else:
            tem_act_end = act.time_end

        if act.scheduled_machine_state == Config.MACHINE_STATE_RUNNING:
            scheduled_run_time += (tem_act_end - temp_act_start)
        elif act.scheduled_machine_state == Config.MACHINE_STATE_OFF:
            scheduled_down_time += (tem_act_end - temp_act_start)
        else:
            unscheduled_time += (tem_act_end - temp_act_start)

    # Add any time unaccounted for
    unscheduled_time += (total_time - (scheduled_down_time + scheduled_run_time))
    if units == "minutes":
        return {"Scheduled Run Time": scheduled_run_time.total_seconds()/60,
                "Scheduled Down Time": scheduled_down_time.total_seconds()/60,
                "Unscheduled Time": unscheduled_time.total_seconds()/60}
    else:
        return {"Scheduled Run Time": scheduled_run_time.total_seconds(),
                "Scheduled Down Time": scheduled_down_time.total_seconds(),
                "Unscheduled Time": unscheduled_time.total_seconds()}


def calculate_activity_percent(machine_id, activity_code_id, time_start: datetime, time_end: datetime):
    """ Returns the percent of time a certain activity code takes up for a certain machine over two times"""
    activities = Activity.query \
        .filter(Activity.machine_id == machine_id) \
        .filter(Activity.activity_code_id == activity_code_id) \
        .filter(Activity.time_end >= time_start) \
        .filter(Activity.time_start <= time_end).all()

    total_time = time_end - time_start
    activity_code_time = timedelta()
    for act in activities:
        activity_code_time += (act.time_end - act.time_start)

    if activity_code_time.total_seconds() == 0:
        return 100
    else:
        return (total_time / activity_code_time) * 100
