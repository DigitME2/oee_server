import logging
from datetime import datetime, timedelta, date, time

import humanize as humanize

from app.data_analysis.helpers import get_daily_values_dict, durations_dict_to_human_readable
from app.default.helpers import get_user_activities, get_machine_activities, get_cropped_start_end_ratio, \
    get_machine_activity_duration
from app.default.models import Activity, ActivityCode, Machine
from app.login.models import User
from config import Config


def get_machine_availability(machine: Machine, time_start: datetime, time_end: datetime):
    """ Takes a machine id and two times, and returns the machine's availability (0-1) for calculating OEE"""

    unplanned_downtime_duration = get_machine_activity_duration(machine, time_start, time_end,
                                                                machine_state=Config.MACHINE_STATE_UNPLANNED_DOWNTIME)
    uptime_duration = get_machine_activity_duration(machine, time_start, time_end,
                                                    machine_state=Config.MACHINE_STATE_UPTIME)
    overtime_duration = get_machine_activity_duration(machine, time_start, time_end,
                                                      machine_state=Config.MACHINE_STATE_OVERTIME)
    runtime = uptime_duration + overtime_duration
    scheduled_uptime = runtime + unplanned_downtime_duration
    if scheduled_uptime == 0:
        return 1
    availability = runtime / scheduled_uptime
    if availability > 1:
        logging.warning(f"Availability of >1 calculated for machine {machine.name} on {time_start.date()}")
    return availability


def get_daily_machine_availability_dict(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's availability on the given date """
    availability_dict = get_daily_values_dict(get_machine_availability, requested_date)
    if human_readable:
        for k, v in availability_dict.items():
            v = v * 100
            availability_dict[k] = f"{round(v, 1)}%"
    return availability_dict


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
            .filter(Activity.end_time >= requested_start) \
            .filter(Activity.start_time <= requested_end).all()

    # Initialise the dictionary that will hold the totals
    activities_dict = {}

    # Add all activity codes to the dictionary.
    act_codes = ActivityCode.query.all()
    for code in act_codes:
        key = code.short_description if use_description_as_key else code.id
        activities_dict[key] = 0

    for act in activities:
        start, end, _ = get_cropped_start_end_ratio(act, requested_start, requested_end)

        # Calculate the duration and add to the dict
        if act.activity_code is None:
            print("here")
        key = act.activity_code.short_description if use_description_as_key else act.activity_code_id
        activities_dict[key] += (end - start).total_seconds()

    if human_readable:
        for k, v in activities_dict.items():
            if v < 60:
                humanize_format = "%0.1f"
            else:
                humanize_format = "%0.0f"
            v = humanize.precisedelta(timedelta(seconds=v), minimum_unit="minutes", format=humanize_format)
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
    """ Return a dictionary of scheduled runtime for every machine for a date"""
    scheduled_runtime_dict = get_daily_values_dict(get_scheduled_machine_runtime, requested_date)
    if human_readable:
        for k, v in scheduled_runtime_dict.items():
            if v < 60:
                humanize_format = "%0.1f"
            else:
                humanize_format = "%0.0f"
            v = humanize.precisedelta(timedelta(seconds=v), minimum_unit="minutes", format=humanize_format)
            scheduled_runtime_dict[k] = v
    return scheduled_runtime_dict


def get_scheduled_machine_runtime(machine: Machine, time_start: datetime, time_end: datetime):
    """ Get the duration a machine is scheduled to run between two times """
    planned_downtime_duration = get_machine_activity_duration(machine, time_start, time_end,
                                                              machine_state=Config.MACHINE_STATE_PLANNED_DOWNTIME)
    total_duration = get_machine_activity_duration(machine, time_start, time_end)
    scheduled_runtime = total_duration - planned_downtime_duration
    return scheduled_runtime


def get_daily_machine_state_dicts(requested_date: date = None, human_readable=False):
    """ Return a dictionary with every machine's state dict on the given date """
    state_dict = get_daily_values_dict(get_machine_state_dict, requested_date)
    if human_readable:
        state_dict = durations_dict_to_human_readable(state_dict)
    return state_dict


def get_machine_state_dict(machine: Machine, time_start: datetime, time_end: datetime):
    """ Return a dictionary with the duration of a machine's states between two times"""
    state = {
        Config.MACHINE_STATE_UPTIME: 0,
        Config.MACHINE_STATE_UNPLANNED_DOWNTIME: 0,
        Config.MACHINE_STATE_PLANNED_DOWNTIME: 0,
        Config.MACHINE_STATE_OVERTIME: 0,
    }
    activity_codes = ActivityCode.query.all()
    activity_duration_dict = get_activity_duration_dict(time_start, time_end, machine)
    for ac in activity_codes:
        duration = activity_duration_dict[ac.id]
        if ac.machine_state == Config.MACHINE_STATE_UPTIME:
            state[Config.MACHINE_STATE_UPTIME] += duration
        elif ac.machine_state == Config.MACHINE_STATE_UNPLANNED_DOWNTIME:
            state[Config.MACHINE_STATE_UNPLANNED_DOWNTIME] += duration
        elif ac.machine_state == Config.MACHINE_STATE_PLANNED_DOWNTIME:
            state[Config.MACHINE_STATE_PLANNED_DOWNTIME] += duration
        elif ac.machine_state == Config.MACHINE_STATE_OVERTIME:
            state[Config.MACHINE_STATE_OVERTIME] += duration
    return state
