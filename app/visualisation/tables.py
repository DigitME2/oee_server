from datetime import datetime, time, date

import pandas as pd
from flask import current_app
from flask_table import Table, Col, create_table

from app.data_analysis.oee.availability import get_activity_duration_dict, get_schedule_dict
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
    operator = Col('Operator')
    actual_run_time = Col('Duration')
    ideal_cycle_time_s = Col(f"Ideal Cycle Time (Seconds)")


def get_work_order_table(start_date: date, end_date: date) -> str:
    start_time = datetime.combine(start_date, time(0, 0, 0, 0))
    end_time = datetime.combine(end_date, time(0, 0, 0, 0))
    jobs = Job.query.filter(Job.start_time <= end_time).filter(Job.end_time >= start_time)
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
        operators = list(set(woj.user.username for woj in wo_jobs if woj.user is not None))
        if len(operators) == 1:
            work_order["operator"] = operators[0]
        elif len(operators) > 1:
            # If there is more than one operator, show them all in a list
            work_order["operator"] = str(operators)

        try:
            start_time = min([woj.start_time for woj in wo_jobs])
            work_order["start"] = start_time.strftime("%d-%m-%y %H:%M")
        except:
            current_app.logger.warning(f"Error getting start time for wo {wo_number}")
            start_time = ""

        end_time = max([woj.end_time for woj in wo_jobs if woj.end_time is not None])
        if end_time is None:
            work_order["end"] = ""
            work_order["actual_run_time"] = (datetime.now() - start_time).total_seconds()/60
        else:
            work_order["end"] = end_time.strftime("%d-%m-%y %H:%M")
            work_order["actual_run_time"] = end_time - start_time

        work_order["actual_run_time"] = sum(wj.quantity_produced for wj in wo_jobs if wj.quantity_produced is not None)
        work_order["ideal_cycle_time_s"] = sum(wj.ideal_cycle_time_s for wj in wo_jobs if wj.ideal_cycle_time_s is not None)
        work_order["quantity_produced"] = sum(wj.quantity_produced for wj in wo_jobs if wj.quantity_produced is not None)
        items.append(work_order)
    table = WOTable(items=items)

    # Add a title manually to the table html
    table_html = f"<h1 id=\"table-title\">" \
                 f"Work Orders {start_date.strftime('%d-%b-%y')} to {end_date.strftime('%d-%b-%y')}" \
                 f"</h1>"\
                 + table.__html__()

    return table_html


def get_job_table(start_date: date, end_date: date, machine_ids) -> str:
    start_time = datetime.combine(start_date, time(0, 0, 0, 0))
    end_time = datetime.combine(end_date, time(0, 0, 0, 0))
    jobs = []
    for machine_id in machine_ids:
        machine_jobs = Job.query\
            .filter(Job.start_time <= end_time)\
            .filter(Job.end_time >= start_time)\
            .filter(Job.machine_id == machine_id).all()
        jobs.extend(machine_jobs)


    items = []
    for job in jobs:
        item = {"job_id": job.id,
                "wo_number": job.wo_number,
                "part_number": job.part_number,
                "ideal_cycle_time_s": job.ideal_cycle_time_s,
                "quantity_produced": job.quantity_produced,
                "rejects": job.quantity_rejects}
        try:
            item["operator"] = str(job.user.username)
        except:
            item["operator"] = ""
        try:
            item["start"] = job.start_time.strftime("%d-%m-%y %H:%M")
        except:
            item["start"] = ""
        try:
            item["end"] = job.end_time.strftime("%d-%m-%y %H:%M")
        except:
            item["end"] = ""
        try:
            if job.end_time is not None:
                item["actual_run_time"] = (job.end_time - job.start_time).total_seconds()/60
            else:
                item["actual_run_time"] = (datetime.now() - job.start_time).total_seconds()/60
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
    ideal_cycle_time_s = Col(f"Ideal Cycle Time (s)")  # todo make this readable when it's on the order of hours
    quantity_produced = Col("Total Qty")
    rejects = Col("Rejects Qty")


def get_raw_database_table(table_name):
    statement = f"SELECT * FROM {table_name};"
    df = pd.read_sql(statement, db.engine)
    table_html = f"<h1 id=\"table-title\"> Database Table {table_name}</h1>" + \
                 df.to_html(classes="dataTable table table-striped table-bordered")

    return table_html


def get_user_activity_table(time_start: datetime, time_end: datetime):
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
        user_dict = get_activity_duration_dict(requested_start=time_start,
                                               requested_end=time_end,
                                               user_id=user.id,
                                               use_description_as_key=True,
                                               units="minutes")
        user_dict = format_dictionary_durations(user_dict)
        user_dict["user"] = user.username

        user_dict.pop(no_user_description)  # Don't show a value for "No User" in the user CSV

        items.append(user_dict)

    table = Tbl(items=items)
    table_html = f"<h1 id=\"table-title\">" \
                 f"Activity Durations {time_start.strftime('%H.%M %d-%b-%y')} to {time_end.strftime('%H.%M %d-%b-%y')}<" \
                 f"/h1>"\
                 + table.__html__()
    return table_html


def get_machine_activity_table(time_start: datetime, time_end: datetime):
    """ Create a CSV listing the amount of time spent for each activity_code."""
    # Dynamically create the table using flask-table
    Tbl = create_table("MachineActivityTable").add_column('machine', Col('Machine Activity Durations (minutes)'))

    # The column names will be the short descriptions of each activity code
    act_codes = ActivityCode.query.all()
    activity_code_descriptions = [code.short_description for code in act_codes]
    for activity_description in activity_code_descriptions:
        Tbl.add_column(activity_description, Col(activity_description))

    # Add the names of scheduled/unscheduled hours as columns
    schedule_dict = get_schedule_dict(1, time_start, time_end)  # Get the dict for any machine, just to parse the keys and create columns
    for key in schedule_dict:
        Tbl.add_column(key, Col(key))

    # Add the class to the table so it's picked up by datatables
    Tbl.classes = ["dataTable table table-striped table-bordered"]

    machines = Machine.query.all()

    items = []
    for machine in machines:
        # Get a dictionary containing all the activities for the machine
        machine_dict = get_activity_duration_dict(requested_start=time_start,
                                                  requested_end=time_end,
                                                  machine_id=machine.id,
                                                  use_description_as_key=True,
                                                  units="minutes")

        # Get a dictionary containing the schedule for the machine
        machine_dict.update(get_schedule_dict(time_start=time_start,
                                              time_end=time_end,
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
