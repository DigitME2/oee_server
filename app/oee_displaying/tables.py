from datetime import datetime, time, date

import pandas as pd
from flask import current_app
from flask_table import Table, Col, create_table

from app.data_analysis.oee import get_activity_duration_dict, get_schedule_dict
from app.default.models import Job, ActivityCode, Machine
from app.extensions import db
from app.login.models import User
from config import Config


class WOTable(Table):
    table_id = "jobTable"
    classes = ["dataTable table table-striped table-bordered"]
    wo_number = Col('WO Number')
    part_number = Col('Part Number')
    start = Col('Start')
    end = Col('End')
    setting_operator = Col('Setting Operator')
    operator = Col('Operator')
    actual_run_time = Col('Duration')
    planned_run_time = Col("Planned Duration (minutes)")
    actual_quantity = Col("Actual Quantity")
    planned_quantity = Col("Planned Quantity")


def get_work_order_table(start_date: date, end_date: date) -> str:
    start_timestamp = datetime.combine(start_date, time(0, 0, 0, 0)).timestamp()
    end_timestamp = datetime.combine(end_date, time(0, 0, 0, 0)).timestamp()
    jobs = Job.query.filter(Job.start_time <= end_timestamp).filter(Job.end_time >= start_timestamp)
    items = []

    # Get every wo_number in the list of jobs
    wo_numbers = []
    for job in jobs:
        if job.wo_number not in wo_numbers:
            wo_numbers.append(job.wo_number)

    # Go through each work order number and add the jobs together to create the final work order numbers
    for wo_number in wo_numbers:
        # Get all of the jobs with the current work order number
        wo_jobs = Job.query.filter_by(wo_number=wo_number).all()
        work_order = {"job_id": str([j.id for j in jobs]),
                      "wo_number": wo_number}

        # If there is more than one part number, show them all in a list
        part_number = list(set(woj.part_number for woj in wo_jobs))
        if len(part_number) == 1:
            work_order["part_number"] = part_number[0]
        else:
            work_order["part_number"] = str(part_number)

        # Set the operators to blank in case either doesn't exist
        work_order["operator"] = ""
        work_order["setting_operator"] = ""
        operators = list(set(woj.user.username for woj in wo_jobs
                                          if woj.user is not None and woj.planned_set_time is None))
        if len(operators) == 1:
            work_order["operator"] = operators[0]
        elif len(operators) > 1:
            # If there is more than one operator, show them all in a list
            work_order["operator"] = str(operators)

        setting_operators = list(set(woj.user.username for woj in wo_jobs
                                          if woj.user is not None and woj.planned_set_time is not None))
        if len(setting_operators) == 1:
            work_order["setting_operator"] = setting_operators[0]
        elif len(setting_operators) > 1:
            # If there is more than one operator, show them all in a list
            work_order["setting_operator"] = str(setting_operators)

        try:
            start_time = datetime.fromtimestamp(min([woj.start_time for woj in wo_jobs]))
            work_order["start"] = start_time.strftime("%d-%m-%y %H:%M")
        except:
            current_app.logger.warning(f"Error getting start time for wo {wo_number}")
            start_time = ""

        end_timestamp = max([woj.end_time for woj in wo_jobs if woj.end_time is not None])
        if end_timestamp is None:
            work_order["end"] = ""
            work_order["actual_run_time"] = datetime.now() - start_time
        else:
            end_time = datetime.fromtimestamp(end_timestamp)
            work_order["end"] = end_time.strftime("%d-%m-%y %H:%M")
            work_order["actual_run_time"] = end_time - start_time

        work_order["actual_run_time"] = sum(wj.actual_quantity for wj in wo_jobs if wj.actual_quantity is not None)
        work_order["planned_run_time"] = sum(wj.planned_run_time for wj in wo_jobs if wj.planned_run_time is not None)
        work_order["actual_quantity"] = sum(wj.actual_quantity for wj in wo_jobs if wj.actual_quantity is not None)
        work_order["planned_quantity"] = sum(wj.planned_quantity for wj in wo_jobs if wj.planned_quantity is not None)
        items.append(work_order)
    table = WOTable(items=items)

    # Add a title manually to the table html
    table_html = f"<h1 id=\"table-title\">" \
                 f"Work Orders {start_date.strftime('%d-%b-%y')} to {end_date.strftime('%d-%b-%y')}" \
                 f"</h1>"\
                 + table.__html__()

    return table_html


def get_job_table(start_date: date, end_date: date) -> str:
    start_timestamp = datetime.combine(start_date, time(0, 0, 0, 0)).timestamp()
    end_timestamp = datetime.combine(end_date, time(0, 0, 0, 0)).timestamp()
    jobs = Job.query.filter(Job.start_time <= end_timestamp).filter(Job.end_time >= start_timestamp)

    items = []
    for job in jobs:
        item = {"job_id": job.id,
                "wo_number": job.wo_number,
                "part_number": job.part_number,
                "planned_run_time": job.planned_run_time,
                "actual_quantity": job.actual_quantity,
                "planned_quantity": job.planned_quantity}
        try:
            item["operator"] = str(job.user.username)
        except:
            item["operator"] = ""
        try:
            item["start"] = datetime.fromtimestamp(job.start_time).strftime("%d-%m-%y %H:%M")
        except:
            item["start"] = ""
        try:
            item["end"] = datetime.fromtimestamp(job.end_time).strftime("%d-%m-%y %H:%M")
        except:
            item["end"] = ""
        try:
            if job.end_time is not None:
                item["actual_run_time"] = datetime.fromtimestamp(job.end_time) - datetime.fromtimestamp(job.start_time)
            else:
                item["actual_run_time"] = datetime.now() - datetime.fromtimestamp(job.start_time)
        except:
            item["actual_run_time"] = ""

        items.append(item)

    table = JobTable(items=items)
    # Add a title manually to the table html
    table_html = f"<h1 id=\"table-title\">" \
                 f"Jobs {start_date.strftime('%d-%b-%y')} to {end_date.strftime('%d-%b-%y')}<" \
                 f"/h1>"\
                 + table.__html__()

    return table_html


class JobTable(Table):
    table_id = "jobTable"
    classes = ["dataTable table table-striped table-bordered"]
    job_id = Col("Job ID")
    wo_number = Col('WO Number')
    part_number = Col('Part Number')
    start = Col('Start')
    end = Col('End')
    operator = Col('Operator')
    actual_run_time = Col('Duration')
    planned_run_time = Col("Planned Duration")
    actual_quantity = Col("Actual Quantity")
    planned_quantity = Col("Planned Quantity")


def get_raw_database_table(table_name):
    statement = f"SELECT * FROM {table_name};"
    df = pd.read_sql(statement, db.engine)
    table_html = f"<h1 id=\"table-title\"> Database Table {table_name}</h1>" + \
                 df.to_html(classes="dataTable table table-striped table-bordered")

    return table_html


def get_user_activity_table(timestamp_start, timestamp_end):
    """Create a table listing the amount of time spent for each activity_code"""

    # Dynamically create the table using flask-table
    Tbl = create_table("UserActivityTable").add_column('user', Col('User Activity Durations (minutes)'))

    # The column names will be the short descriptions of each activity code
    act_codes = ActivityCode.query.all()
    activity_code_descriptions = [code.short_description for code in act_codes]

    # Remove the value for no user, so we don't show a value for "No User" in the user CSV
    no_user_description = ActivityCode.query.get(Config.NO_USER_CODE_ID).short_description
    activity_code_descriptions.remove(no_user_description)

    for activity_description in activity_code_descriptions:
        Tbl.add_column(activity_description, Col(activity_description))

    # Add the html class to the table so it's picked up by datatables
    Tbl.classes = ["dataTable table table-striped table-bordered"]

    users = User.query.all()

    items = []
    no_user_description = ActivityCode.query.get(Config.NO_USER_CODE_ID).short_description
    for user in users:
        # Get a dict with the activities in
        user_dict = get_activity_duration_dict(requested_start=timestamp_start,
                                               requested_end=timestamp_end,
                                               user_id=user.id,
                                               use_description_as_key=True,
                                               units="minutes")
        user_dict = format_dictionary_durations(user_dict)
        user_dict["user"] = user.username

        user_dict.pop(no_user_description)  # Don't show a value for "No User" in the user CSV

        items.append(user_dict)

    table = Tbl(items=items)
    start = datetime.fromtimestamp(timestamp_start)
    end = datetime.fromtimestamp(timestamp_end)
    table_html = f"<h1 id=\"table-title\">" \
                 f"Activity Durations {start.strftime('%H.%M %d-%b-%y')} to {end.strftime('%H.%M %d-%b-%y')}<" \
                 f"/h1>"\
                 + table.__html__()
    return table_html


def get_machine_activity_table(timestamp_start, timestamp_end):
    """ Create a CSV listing the amount of time spent for each activity_code."""
    # Dynamically create the table using flask-table
    Tbl = create_table("MachineActivityTable").add_column('machine', Col('Machine Activity Durations (minutes)'))

    # The column names will be the short descriptions of each activity code
    act_codes = ActivityCode.query.all()
    activity_code_descriptions = [code.short_description for code in act_codes]
    for activity_description in activity_code_descriptions:
        Tbl.add_column(activity_description, Col(activity_description))

    # Add the names of scheduled/unscheduled hours as columns
    schedule_dict = get_schedule_dict(1, timestamp_start, timestamp_end)  # Get the dict for any machine, just to parse the keys and create columns
    for key in schedule_dict:
        Tbl.add_column(key, Col(key))

    # Add the class to the table so it's picked up by datatables
    Tbl.classes = ["dataTable table table-striped table-bordered"]

    machines = Machine.query.all()

    items = []
    for machine in machines:
        # Get a dictionary containing all the activities for the machine
        machine_dict = get_activity_duration_dict(requested_start=timestamp_start,
                                                  requested_end=timestamp_end,
                                                  machine_id=machine.id,
                                                  use_description_as_key=True,
                                                  units="minutes")

        # Get a dictionary containing the schedule for the machine
        machine_dict.update(get_schedule_dict(timestamp_start=timestamp_start,
                                              timestamp_end=timestamp_end,
                                              machine_id=machine.id,
                                              units="minutes"))
        # Format the times in the dictionary (Do this before adding the machine names)
        machine_dict = format_dictionary_durations(machine_dict)

        # The first column will be the name of the machine
        machine_dict["machine"] = machine.name

        items.append(machine_dict)

    table = Tbl(items=items)
    return table.__html__()


def format_dictionary_durations(dictionary):
    """ Takes a dict with values in seconds and rounds the values for legibility"""
    formatted_dict = {}
    for k, v in dictionary.items():
        try:
            formatted_dict[k] = round(v)
        except TypeError:
            pass
    return formatted_dict
