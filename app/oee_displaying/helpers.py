import pandas as pd
from flask_table import Table, Col

from datetime import datetime, time, date

from flask import current_app

from app import db
from app.data_analysis.oee import get_schedule_dict, get_machine_runtime
from app.default.db_helpers import get_legible_duration, get_current_machine_activity_id
from app.default.models import Machine, Activity, Job
from app.login.models import User, UserSession


def get_machine_status(machine_id):
    """ Returns a dictionary holding information for the status a machine"""
    machine = Machine.query.get_or_404(machine_id)
    # Get the current user logged on to the machine
    machine_user_id = get_machine_current_user(machine.id)
    if machine_user_id == -1:
        machine_user_text = "No user"
    else:
        try:
            machine_user_text = User.query.get(machine_user_id).username
        except:
            current_app.logger.warning(f"Error getting user id {machine_user_id}")
            machine_user_text = "Error getting user"

    # Get the current activity on the machine
    current_activity_id = get_current_machine_activity_id(target_machine_id=machine.id)
    if current_activity_id is None:
        activity_text = "No Activity"
        job_text = "No Job"
        duration = ""
    else:
        current_machine_activity = Activity.query.get(current_activity_id)
        activity_text = current_machine_activity.activity_code.short_description
        try:
            job_text = current_machine_activity.job.wo_number
        except AttributeError:  # When there's no job
            job_text = "No job"
        duration = get_legible_duration(timestamp_start=current_machine_activity.timestamp_start,
                                        timestamp_end=datetime.now().timestamp())

    return {"machine_name": machine.name,
            "machine_user": machine_user_text,
            "machine_activity": activity_text,
            "machine_job": job_text,
            "duration": duration}


def get_machine_current_user(machine_id):
    """ Get the current user that is logged onto a machine"""
    user_sessions = UserSession.query.filter_by(machine_id=machine_id, active=True).all()
    # If there's more than one active session (there shouldn't be), get the most recent and end the others
    if len(user_sessions) > 1:
        current_app.logger.warning(f"Multiple user sessions found for machine id {machine_id}")
        # Get the current activity by grabbing the one with the most recent start time
        most_recent_session = max(user_sessions, key=lambda user_session: user_session.timestamp_login)
        user_sessions.remove(most_recent_session)

        for us in user_sessions:
            current_app.logger.warning(f"Ending session {us}")
            us.timestamp_logout = datetime.now().timestamp()
            db.session.add(us)
            db.session.commit()
    elif len(user_sessions) == 1:
        return user_sessions[0].user_id
    elif len(user_sessions) == 0:
        return -1


def parse_requested_machine_list(requested_machines):
    """Parse the machines selected in a dropdown list and return a list of the machine ids"""
    if requested_machines == "all":
        return list(machine.id for machine in Machine.query.all())

    # If the machines argument begins with g_ it means a group of machines has been selected
    elif requested_machines[0:2] == "g_":
        group_id = requested_machines[2:]
        return list(machine.id for machine in Machine.query.filter_by(group_id=group_id))

    # If the argument begins with m_ it represents just one machine
    elif requested_machines[0:2] == "m_":
        return list(requested_machines[2:])

    else:
        return None

class WOTable(Table):
    table_id = "jobTable"
    wo_number = Col('WO Number')
    part_number = Col('Part Number')
    start = Col('Start')
    end = Col('End')
    setting_operator = Col('Setting Operator')
    operator = Col('Operator')
    actual_run_time = Col('Duration')
    planned_run_time = Col("Planned Duration")
    actual_quantity = Col("Actual Quantity")
    planned_quantity = Col("Planned Quantity")


def get_work_order_table(start_date, end_date):
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

    return table.__html__()



def get_job_table(start_date, end_date):
    # todo slim down to only get requested stuffs
    # todo conditional formatting for duration vs planned duration
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

    return table.__html__()


class JobTable(Table):
    table_id = "jobTable"
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

