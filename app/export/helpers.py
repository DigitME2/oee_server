import csv
import os
import pandas as pd
from datetime import datetime, timedelta

from app.data_analysis.oee import get_activity_dict, get_schedule_dict
from app.default.models import ActivityCode, Machine
from app.login.models import User

from config import Config


def format_dictionary_durations_for_csv(dictionary):
    """ Takes a dict with values in seconds and formats the values for entry into a csv"""
    formatted_dict = {}
    for k, v in dictionary.items():
        formatted_dict[k] = round(v)
    return formatted_dict


def get_temp_filepath(name):
    """ Returns the filepath for a temporary file"""
    directory = os.path.join('app', 'static', 'temp')
    if not os.path.exists(directory):
        os.mkdir(directory)
    return os.path.abspath(os.path.join(directory, name))


def create_users_csv(time_start, time_end):
    """ Create a CSV listing the amount of time spent for each activity_code.
    This function returns the filepath where the file is saved"""
    users = User.query.all()
    act_codes = ActivityCode.query.all()
    no_user_description = ActivityCode.query.get(Config.NO_USER_CODE_ID).short_description
    filepath = get_temp_filepath("users.csv")
    with open(filepath, 'w+') as csv_file:
        headers = [' ']  # No header for user column
        activity_code_descriptions = [code.short_description for code in act_codes]
        activity_code_descriptions.remove(no_user_description)  # Don't show a value for "No User" in the user CSV
        headers.extend(activity_code_descriptions)

        # Use a dictwriter to write the actual data to the file
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        # Write the headers
        writer.writeheader()

        for user in users:
            user_dict = get_activity_dict(time_start=time_start,
                                          time_end=time_end,
                                          user_id=user.id,
                                          use_description_as_key=True)
            user_dict.pop(no_user_description)  # Don't show a value for "No User" in the user CSV
            # Format the durations to be readable
            user_dict = format_dictionary_durations_for_csv(user_dict)
            user_dict[" "] = user.username  # No header for user column
            writer.writerow(user_dict)

        return filepath


def create_machines_csv(time_start, time_end):
    machines = Machine.query.all()
    act_codes = ActivityCode.query.all()
    filepath = get_temp_filepath("users.csv")
    with open(filepath, 'w+') as csv_file:
        headers = [' ']  # No header for user column
        activity_code_descriptions = [code.short_description for code in act_codes]
        headers.extend(activity_code_descriptions)

        schedule_dict = get_schedule_dict(1, time_start, time_end)  # Get any dict to parse the keys
        for key in schedule_dict:
            headers.append(key)

        # Use a dictwriter to write the actual data to the file
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        # Write the headers
        writer.writeheader()

        for machine in machines:
            machine_dict = get_activity_dict(time_start=time_start, time_end=time_end, machine_id=machine.id,
                                             use_description_as_key=True)
            machine_dict.update(get_schedule_dict(time_start=time_start, time_end=time_end, machine_id=machine.id))
            machine_dict = format_dictionary_durations_for_csv(machine_dict)
            machine_dict[" "] = machine.name  # No header for user column
            writer.writerow(machine_dict)

        return filepath
