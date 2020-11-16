from datetime import datetime, timedelta, time
from app.extensions import db
from app.data_analysis.models import DailyOEE
from app.default.models import Activity, ActivityCode, ScheduledActivity, MachineGroup
from app.default.db_helpers import get_machine_activities, get_user_activities

from config import Config


def get_machine_runtime(machine_id, requested_start, requested_end, units="seconds"):
    """ Takes a machine id and two timestamps, and returns the amount of time the machine was running """
    # Get all of the activities for the machine between the two given times, where the machine is up
    activities = Activity.query \
        .filter(Activity.machine_id == machine_id) \
        .filter(Activity.machine_state == Config.MACHINE_STATE_RUNNING) \
        .filter(Activity.timestamp_end >= requested_start) \
        .filter(Activity.timestamp_start <= requested_end).all()

    run_time = 0
    for act in activities:
        run_time += (act.timestamp_end - act.timestamp_start)
    if units == "minutes":
        return run_time/60
    elif units == "seconds":
        return run_time


def get_activity_duration_dict(requested_start, requested_end, machine_id=None, user_id=None, use_description_as_key=False, units="seconds"):
    """ Returns a dict containing the total duration of each activity_code between two timestamps in the format:
    activity_code_id: duration(seconds) e.g. 1: 600
    If use_description_as_key is passed, the activity_code_id is replaced with its description e.g. uptime: 600"""
    if user_id:
        # Get all of the activities for a user
        activities = get_user_activities(user_id=user_id,
                                         timestamp_start=requested_start,
                                         timestamp_end=requested_end)
    elif machine_id:
        # Get all of the activities for a machine
        activities = get_machine_activities(machine_id=machine_id,
                                            timestamp_start=requested_start,
                                            timestamp_end=requested_end)
    else:
        # Get all the activities
        activities = Activity.query \
            .filter(Activity.timestamp_end >= requested_start) \
            .filter(Activity.timestamp_start <= requested_end).all()

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
        if act.timestamp_start is not None and act.timestamp_start > requested_start:
            start = act.timestamp_start
        else:
            start = requested_start

        # If the activity extends past the requested end or has no end, crop it to the requested end (or current time)
        if act.timestamp_end is None or act.timestamp_start > requested_end:
            end = min([requested_end, datetime.now().timestamp()])
        else:
            end = act.timestamp_end

        # Calculate the duration and add to the dict
        if use_description_as_key:
            activities_dict[act.activity_code.short_description] += (end - start)
        else:
            activities_dict[act.activity_code_id] += (end - start)
    # Convert to minutes if requested
    if units == "minutes":
        for n in activities_dict:
            activities_dict[n] = activities_dict[n]/60
    return activities_dict


def get_schedule_dict(machine_id, timestamp_start, timestamp_end, units="seconds"):
    """ Takes a machine id and two times, and returns a dict with:
    scheduled_run_time
    scheduled_down_time
    unscheduled_time"""
    # Get all the scheduled activities
    activities = ScheduledActivity.query \
        .filter(ScheduledActivity.machine_id == machine_id) \
        .filter(ScheduledActivity.timestamp_end >= timestamp_start) \
        .filter(ScheduledActivity.timestamp_start <= timestamp_end).all()

    total_time = timestamp_end - timestamp_start
    scheduled_run_time = 0
    scheduled_down_time = 0
    unscheduled_time = 0
    for act in activities:
        # If the activity extends past the  start or end, crop it short
        if act.timestamp_start < timestamp_start:
            start = timestamp_start
        else:
            start = act.timestamp_start
        if act.timestamp_end > timestamp_end:
            end = timestamp_end
        else:
            end = act.timestamp_end

        if act.scheduled_machine_state == Config.MACHINE_STATE_RUNNING:
            scheduled_run_time += (end - start)
        elif act.scheduled_machine_state == Config.MACHINE_STATE_OFF:
            scheduled_down_time += (end - start)
        else:
            unscheduled_time += (end - start)

    # Add any time unaccounted for
    unscheduled_time += (total_time - (scheduled_down_time + scheduled_run_time))
    if units == "minutes":
        scheduled_run_time = scheduled_run_time/60
        scheduled_down_time = scheduled_down_time/60
        unscheduled_time = unscheduled_time/60

    return {"Scheduled Run Time": scheduled_run_time,
            "Scheduled Down Time": scheduled_down_time,
            "Unscheduled Time": unscheduled_time}


def calculate_activity_percent(machine_id, activity_code_id, timestamp_start, timestamp_end):
    """ Returns the percent of time a certain activity code takes up for a certain machine over two timestamps"""
    activities = Activity.query \
        .filter(Activity.machine_id == machine_id) \
        .filter(Activity.activity_code_id == activity_code_id) \
        .filter(Activity.timestamp_end >= timestamp_start) \
        .filter(Activity.timestamp_start <= timestamp_end).all()

    total_time = timestamp_end - timestamp_start
    activity_code_time = 0
    for act in activities:
        activity_code_time += (act.timestamp_end - act.timestamp_start)

    if activity_code_time == 0:
        return 0
    else:
        return (total_time / activity_code_time) * 100


def calculate_activity_time(machine_id, activity_code_id, timestamp_start, timestamp_end):
    """ Returns the time a certain activity code takes up for a certain machine over two timestamps"""
    activities = Activity.query \
        .filter(Activity.machine_id == machine_id) \
        .filter(Activity.activity_code_id == activity_code_id) \
        .filter(Activity.timestamp_end >= timestamp_start) \
        .filter(Activity.timestamp_start <= timestamp_end).all()

    activity_code_time = 0
    for act in activities:
        activity_code_time += (act.timestamp_end - act.timestamp_start)
    return activity_code_time


def calculate_machine_oee(machine_id, timestamp_start, timestamp_end):
    """ Takes a machine id and two times, and returns the machine's OEE figure as a percent
    Note: currently only calculates availability, not performance and quality which are part of the oee calculation"""
    #todo need to have a think about what happens here if there are no activities or scheduled activities
    # Do we save a 0 or None?

    #todo sanity check - warn user if over 100 or if there are no scheduled times

    #todo test this make sure answers are correct
    runtime = get_machine_runtime(machine_id, timestamp_start, timestamp_end)
    scheduled_uptime = get_schedule_dict(machine_id, timestamp_start, timestamp_end, units="minutes")["scheduled_run_time"]
    if scheduled_uptime == 0:
        return 0
    availability = runtime / scheduled_uptime
    oee = availability * 100
    return oee


def get_daily_machine_oee(machine_id, date):
    """ Takes a machine id and a dates, then gets the oee for the day and saves the figure to database """
    #todo dont run for current day or future. Maybe add future validation to web form
    daily_machine_oee = DailyOEE.query.filter_by(machine_id=machine_id, date=date).first()
    # If the OEE figure is missing, call the function to calculate the missing values and save in database
    if daily_machine_oee is None:
        start = datetime.combine(date=date, time=time(hour=0, minute=0, second=0, microsecond=0))
        end = start + timedelta(days=1)
        oee = calculate_machine_oee(machine_id, timestamp_start=start.timestamp(), timestamp_end=end.timestamp())
        daily_machine_oee = DailyOEE(machine_id=machine_id, date=date, oee=oee)
        db.session.add(daily_machine_oee)
        db.session.commit()

    return daily_machine_oee.oee


def get_daily_group_oee(group_id, date):
    """Get the mean OEE figure for a group of machines on a particular day"""
    group = MachineGroup.query.filter_by(id=group_id).first()
    machine_oees = []
    for machine in group.machines:
        # For each machine add the oee figure to the list
        machine_oees.append(get_daily_machine_oee(machine.id, date))
    if machine_oees is None:
        return 0
    mean_oee = sum(machine_oees) / len(machine_oees)
    return mean_oee
