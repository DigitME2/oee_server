from datetime import datetime, timedelta

from flask import current_app

from app.data_analysis import OEECalculationException
from app.default.db_helpers import get_user_activities, get_machine_activities
from app.default.models import Activity, ActivityCode, ScheduledActivity
from config import Config


def calculate_machine_availability(machine_id, time_start: datetime, time_end: datetime):
    """ Takes a machine id and two times, and returns the machine's availability for calculating OEE"""

    if time_end > datetime.now():
        current_app.logger.warn(f"Machine oee requested for future date {time_end.strftime(('%Y-%m-%d'))}")
        raise OEECalculationException("Machine OEE requested for future date")
    runtime = get_machine_runtime(machine_id, time_start, time_end, units="seconds")
    scheduled_uptime = get_schedule_dict(machine_id, time_start, time_end, units="seconds")["Scheduled Run Time"]
    if scheduled_uptime == 0:
        raise OEECalculationException("No scheduled activity for requested OEE")
    availability = runtime / scheduled_uptime
    current_app.logger.debug(f"machine id {machine_id} availability {time_start} = {availability}")
    return availability


def get_machine_runtime(machine_id, requested_start: datetime, requested_end: datetime, units="seconds"):
    """ Takes a machine id and two times, and returns the amount of time the machine was running """
    # Get all of the activities for the machine between the two given times, where the machine is up
    activities = Activity.query \
        .filter(Activity.machine_id == machine_id) \
        .filter(Activity.machine_state == Config.MACHINE_STATE_RUNNING) \
        .filter(Activity.time_end >= requested_start) \
        .filter(Activity.time_start <= requested_end).all()

    run_time = 0
    for act in activities:
        run_time += (act.time_end - act.time_start).seconds
    if units == "minutes":
        return run_time / 60
    elif units == "seconds":
        return run_time


def get_activity_duration_dict(requested_start: datetime, requested_end: datetime, machine_id=None, user_id=None, use_description_as_key=False, units="seconds"):
    """ Returns a dict containing the total duration of each activity_code between two times in the format:
    activity_code_id: duration(seconds) e.g. 1: 600
    If use_description_as_key is passed, the activity_code_id is replaced with its description e.g. uptime: 600"""

    if user_id:
        # Get all of the activities for a user
        activities = get_user_activities(user_id=user_id,
                                         time_start=requested_start,
                                         time_end=requested_end)
    elif machine_id:
        # Get all of the activities for a machine
        activities = get_machine_activities(machine_id=machine_id,
                                            time_start=requested_start,
                                            time_end=requested_end)
    else:
        # Get all the activities
        activities = Activity.query \
            .filter(Activity.time_end >= requested_start) \
            .filter(Activity.time_start <= requested_end).all()

    # Initialise the dictionary that will hold the totals
    activities_dict = {}

    # Add all activity codes to the dictionary.
    # If use_descriptions_as_key, then the key is the description of the activity code. Otherwise it is the code id
    act_codes = ActivityCode.query.all()
    for code in act_codes:
        if use_description_as_key:
            activities_dict[code.short_description] = 0
        else:
            activities_dict[code.id] = 0

    for act in activities:
        # If the activity starts before the requested start, crop it to the requested start time
        if act.time_start is not None and act.time_start > requested_start:
            start = act.time_start
        else:
            start = requested_start

        # If the activity extends past the requested end or has no end, crop it to the requested end (or current time)
        if act.time_end is None or act.time_start > requested_end:
            end = min([requested_end, datetime.now()])
        else:
            end = act.time_end

        # Calculate the duration and add to the dict
        if use_description_as_key:
            activities_dict[act.activity_code.short_description] += (end - start)
        else:
            activities_dict[act.activity_code_id] += (end - start)
    # Convert to minutes if requested
    if units == "minutes":
        for n in activities_dict:
            activities_dict[n] = activities_dict[n] / 60
    return activities_dict


def get_schedule_dict(machine_id, time_start: datetime, time_end: datetime, units="seconds"):
    """ Takes a machine id and two times, and returns a dict with:
    scheduled_run_time
    scheduled_down_time
    unscheduled_time"""
    # Get all the scheduled activities
    activities = ScheduledActivity.query \
        .filter(ScheduledActivity.machine_id == machine_id) \
        .filter(ScheduledActivity.time_end >= time_start) \
        .filter(ScheduledActivity.time_start <= time_end).all()

    total_time = time_end - time_start
    scheduled_run_time = timedelta()
    scheduled_down_time = timedelta()
    unscheduled_time = timedelta()
    for act in activities:
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
        return {"Scheduled Run Time": scheduled_run_time.seconds/60,
                "Scheduled Down Time": scheduled_down_time.seconds/60,
                "Unscheduled Time": unscheduled_time.seconds/60}
    else:
        return {"Scheduled Run Time": scheduled_run_time.seconds,
                "Scheduled Down Time": scheduled_down_time.seconds,
                "Unscheduled Time": unscheduled_time.seconds}


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

    if activity_code_time.seconds == 0:
        return 100
    else:
        return (total_time / activity_code_time) * 100
