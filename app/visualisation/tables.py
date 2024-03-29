from datetime import datetime, time, date, timedelta

import pandas as pd
from flask import current_app
from flask_table import Table, Col, create_table

from app.data_analysis.helpers import get_daily_values_dict
from app.data_analysis.oee.availability import get_activity_duration_dict, get_daily_machine_availability_dict, \
    get_daily_scheduled_runtime_dicts, get_daily_activity_duration_dict, get_daily_machine_state_dicts
from app.data_analysis.oee.oee import get_daily_machine_oee, get_daily_oee_dict
from app.data_analysis.oee.performance import get_daily_performance_dict, get_daily_target_production_amount_dict, \
    get_daily_production_dict
from app.data_analysis.oee.quality import get_daily_quality_dict
from app.default.helpers import get_jobs, get_machine_activities
from app.default.models import Job, ActivityCode, Machine
from app.extensions import db
from app.login.models import User
from app.visualisation.helpers import get_daily_machine_production
from config import Config


class OEEReportTable(Table):
    def sort_url(self, col_id, reverse=False):
        pass

    table_id = "daily-oee-table"
    classes = ["dataTable table table-striped table-bordered"]
    machine = Col('Machine')
    total_time = Col('Total Duration (min)')
    scheduled_downtime = Col('Scheduled Downtime (min)')
    unscheduled_downtime = Col('Unscheduled Downtime (min)')
    uptime = Col('Uptime Duration (min)')
    target = Col('Expected Qty')
    total_qty = Col('Actual Qty')
    rejects = Col('Rejects Qty')
    availability = Col('Availability (%)')
    performance = Col('Performance (%)')
    quality = Col('Quality (%)')
    oee = Col('OEE (%)')


def get_oee_report_table(requested_date: date) -> str:
    good_dict, rejects_dict = get_daily_production_dict(requested_date, human_readable=False)
    production_dict = {}
    for k, v in good_dict.items():
        production_dict[k] = good_dict[k] + rejects_dict[k]
    availability_dict = get_daily_machine_availability_dict(requested_date, human_readable=False)
    performance_dict = get_daily_performance_dict(requested_date, human_readable=False)
    quality_dict = get_daily_quality_dict(requested_date, human_readable=False)
    oee_dict = get_daily_oee_dict(requested_date, human_readable=False)
    scheduled_runtime_dict = get_daily_scheduled_runtime_dicts(requested_date, human_readable=False)
    state_dict = get_daily_machine_state_dicts(requested_date, human_readable=False)
    target_production_dict = get_daily_target_production_amount_dict(requested_date)
    activity_durations_dict = get_daily_activity_duration_dict(requested_date, human_readable=False)

    table_rows = []
    for machine in Machine.query.all():
        total_runtime = state_dict[machine.id][Config.MACHINE_STATE_UPTIME] + state_dict[machine.id][Config.MACHINE_STATE_OVERTIME]
        total_time = total_runtime + state_dict[machine.id][Config.MACHINE_STATE_PLANNED_DOWNTIME] + \
                     state_dict[machine.id][Config.MACHINE_STATE_UNPLANNED_DOWNTIME]
        table_row = {'machine': machine.name,
                     'total_time': round(total_time / 60),
                     'scheduled_downtime': round(state_dict[machine.id][Config.MACHINE_STATE_PLANNED_DOWNTIME] / 60),
                     'unscheduled_downtime': round(state_dict[machine.id][Config.MACHINE_STATE_UNPLANNED_DOWNTIME] / 60),
                     'uptime': round(total_runtime / 60),
                     'target': round(target_production_dict[machine.id]),
                     'total_qty': round(production_dict[machine.id]),
                     'rejects': round(rejects_dict[machine.id]),
                     'availability': round(availability_dict[machine.id] * 100, 1),
                     'performance': round(performance_dict[machine.id] * 100, 1),
                     'quality': round(quality_dict[machine.id] * 100, 1),
                     'oee': round(oee_dict[machine.id] * 100, 1)}
        table_rows.append(table_row)
    table = OEEReportTable(table_rows)
    table_html = f"<h1 id=\"table-title\">" \
                 f"OEE Report" \
                 f"</h1>" \
                 + table.__html__()
    return table_html


def get_oee_table(start_date: date, end_date: date) -> str:
    if end_date >= datetime.now().date():
        end_date = (datetime.now() - timedelta(days=1)).date()
    machines = Machine.query.all()
    dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    items = []
    OEETable = create_table().add_column('machine', Col('Machine'))
    OEETable.classes = ["dataTable table table-striped table-bordered"]
    for machine in machines:
        item = {"machine": machine.name}
        for d in dates:
            oee = (get_daily_machine_oee(machine=machine, date=d) * 100)
            column_header = d.strftime("%Y/%m/%d")
            OEETable.add_column(column_header, Col(column_header))
            item[column_header] = ("%.1f" % oee)
        items.append(item)
    table = OEETable(items)
    table_html = f"<h1 id=\"table-title\">" \
                 f"OEE" \
                 f"</h1>" \
                 + table.__html__()

    return table_html


def get_machine_production_table(start_date: date, end_date: date):
    if end_date >= datetime.now().date():
        end_date = (datetime.now() - timedelta(days=1)).date()
    machines = Machine.query.all()
    dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    items = []
    ProdTable = create_table().add_column('machine', Col('Machine'))
    ProdTable.classes = ["dataTable table table-striped table-bordered"]
    for machine in machines:
        item = {"machine": machine.name}
        for d in dates:
            production_quantity = get_daily_machine_production(machine=machine, d=d)
            column_header = d.strftime("%Y/%m/%d")
            ProdTable.add_column(column_header, Col(column_header))
            item[column_header] = production_quantity
        items.append(item)
    table = ProdTable(items)
    table_html = f"<h1 id=\"table-title\">" \
                 f"Quantity Produced" \
                 f"</h1>" \
                 + table.__html__()

    return table_html


class WOTable(Table):
    table_id = "jobTable"
    classes = ["dataTable table table-striped table-bordered"]
    job_number = Col('WO Number')
    part_number = Col('Part Number')
    start = Col('Start')
    end = Col('End')
    operator = Col('Operator')
    actual_run_time = Col('Duration')
    ideal_cycle_time_s = Col(f"Ideal Cycle Time (Seconds)")


def get_work_order_table(start_date: date, end_date: date) -> str:
    # todo This is an old table we don't use anymore. The jobs are grouped together by job number. Should be merged
    #  into the other job table as an option somehow
    start_time = datetime.combine(start_date, time(0, 0, 0, 0))
    end_time = datetime.combine(end_date + timedelta(days=1), time(0, 0, 0, 0))
    jobs = get_jobs(start_time, end_time)
    items = []

    # Get every job_number in the list of jobs
    job_numbers = []
    for job in jobs:
        if job.job_number not in job_numbers:
            job_numbers.append(job.job_number)

    # Go through each job number and add the jobs together to create the final job numbers
    for job_number in job_numbers:
        # Get all jobs with the current job order number
        job_number_jobs = Job.query.filter_by(job_number=job_number).all()
        work_order = {"job_id": str([j.id for j in job_number_jobs]),
                      "job_number": job_number}

        # If there is more than one part number, show them all in a list
        part_number = list(set(woj.part_number for woj in job_number_jobs))
        if len(part_number) == 1:
            work_order["part_number"] = part_number[0]
        else:
            work_order["part_number"] = str(part_number)

        # Set the operators to blank in case either doesn't exist
        work_order["operator"] = ""
        operators = list(set(woj.user.username for woj in job_number_jobs if woj.user is not None))
        if len(operators) == 1:
            work_order["operator"] = operators[0]
        elif len(operators) > 1:
            # If there is more than one operator, show them all in a list
            work_order["operator"] = str(operators)

        try:
            start_time = min([woj.start_time for woj in job_number_jobs])
            work_order["start"] = start_time.strftime("%d-%m-%y %H:%M")
        except:
            current_app.logger.warning(f"Error getting start time for wo {job_number}")
            start_time = ""

        end_time = max([woj.end_time for woj in job_number_jobs if woj.end_time is not None])
        if end_time is None:
            work_order["end"] = ""
            work_order["actual_run_time"] = (datetime.now() - start_time).total_seconds() / 60
        else:
            work_order["end"] = end_time.strftime("%d-%m-%y %H:%M")
            work_order["actual_run_time"] = end_time - start_time

        # FIXME what is the line below
        # work_order["actual_run_time"] = sum(j.quantity_good for j in job_number_jobs if j.quantity_good is not None)
        work_order["ideal_cycle_time_s"] = sum(
            j.ideal_cycle_time_s for j in job_number_jobs if j.ideal_cycle_time_s is not None)
        work_order["quantity_good"] = sum(j.quantity_good for j in job_number_jobs if j.quantity_good is not None)
        items.append(work_order)
    table = WOTable(items=items)

    # Add a title manually to the table html
    table_html = f"<h1 id=\"table-title\">" \
                 f"Work Orders {start_date.strftime('%d-%b-%y')} to {end_date.strftime('%d-%b-%y')}" \
                 f"</h1>" \
                 + table.__html__()

    return table_html


def get_job_table(start_date: date, end_date: date, machines) -> str:
    start_time = datetime.combine(start_date, time(0, 0, 0, 0))
    end_time = datetime.combine(end_date + timedelta(days=1), time(0, 0, 0, 0))
    jobs = []
    for machine in machines:
        machine_jobs = get_jobs(start_time, end_time, machine=machine)
        jobs.extend(machine_jobs)

    items = []
    for job in jobs:
        item = {"job_id": job.id,
                "job_number": job.job_number,
                "part_number": job.part_number,
                "ideal_cycle_time_s": job.ideal_cycle_time_s,
                "quantity_good": job.get_total_good_quantity(),
                "rejects": job.get_total_reject_quantity()}
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
                item["actual_run_time"] = (job.end_time - job.start_time).total_seconds() / 60
            else:
                item["actual_run_time"] = str((datetime.now() - job.start_time).total_seconds() / 60)
        except:
            item["actual_run_time"] = ""

        items.append(item)

    table = JobTable(items=items)
    # Add a title manually to the table html
    table_html = f"<h1 id=\"table-title\">" \
                 f"Jobs {start_date.strftime('%d-%b-%y')} to {end_date.strftime('%d-%b-%y')}<" \
                 f"/h1>" \
                 + table.__html__()

    return table_html


class JobTable(Table):
    table_id = "jobTable"
    classes = ["dataTable table table-striped table-bordered"]
    job_id = Col("Job ID")
    job_number = Col('Job Number')
    start = Col('Start')
    end = Col('End')
    ideal_cycle_time_s = Col(f"Ideal Cycle Time (s)")  #
    quantity_good = Col("Good Qty")
    rejects = Col("Rejects Qty")


def get_user_activity_table(time_start: datetime, time_end: datetime):
    """Create a table listing the amount of time spent for each activity_code"""

    # Dynamically create the table using flask-table
    Tbl = create_table("UserActivityTable").add_column('user', Col('User Activity Durations (minutes)'))

    # The column names will be the short descriptions of each activity code
    act_codes = ActivityCode.query.all()
    activity_code_descriptions = [code.short_description for code in act_codes]

    for activity_description in activity_code_descriptions:
        Tbl.add_column(activity_description, Col(activity_description))

    # Add the html class to the table so it's picked up by datatables
    Tbl.classes = ["dataTable table table-striped table-bordered"]

    users = User.query.all()

    items = []
    for user in users:
        # Get a dict with the activities in
        user_dict = get_activity_duration_dict(requested_start=time_start,
                                               requested_end=time_end,
                                               user=user,
                                               use_description_as_key=True,
                                               units="minutes")
        user_dict = format_dictionary_durations(user_dict)
        user_dict["user"] = user.username

        items.append(user_dict)

    table = Tbl(items=items)
    table_html = f"<h1 id=\"table-title\">" \
                 f"Activity Durations {time_start.strftime('%H.%M %d-%b-%y')} to {time_end.strftime('%H.%M %d-%b-%y')}<" \
                 f"/h1>" \
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

    # Add the class to the table so it's picked up by datatables
    Tbl.classes = ["dataTable table table-striped table-bordered"]

    machines = Machine.query.all()

    items = []
    for machine in machines:
        # Get a dictionary containing all the activities for the machine
        machine_dict = get_activity_duration_dict(requested_start=time_start,
                                                  requested_end=time_end,
                                                  machine=machine,
                                                  use_description_as_key=True,
                                                  units="minutes")

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
