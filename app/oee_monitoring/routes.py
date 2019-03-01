from app import db
from app.oee_monitoring import bp
from app.oee_monitoring.forms import StartForm
from app.default.models import Activity, ActivityCode, Machine, Job
from flask import render_template, redirect, url_for, request, Response
from flask_login import login_required, current_user
from app.oee_displaying.graph_helper import create_machine_gantt

from time import time


@bp.route('/startjob', methods=['GET', 'POST'])
@login_required
def start_job():
    # todo check if job is already in progress for user
    """ The page where a user will start a job"""
    user = current_user
    form = StartForm()
    if form.validate_on_submit():
        job_number = form.job_no
        machine_number = form.machine_number
        start_time = time()
        job = Job(start_time=start_time, user_id=user.id, job_number=job_number, machine_number=machine_number)
        db.session.add(job)
        db.session.commit()
        redirect(url_for('job_in_progress'))
    nav_bar_title = "Start a new job"
    return render_template('oee_monitoring/startjob.html',
                           title="New Job",
                           form=form,
                           user=user,
                           nav_bar_title=nav_bar_title)


@bp.route('/jobinprogress', methods=['GET', 'POST'])
@login_required
def job_in_progress():
    """ The page shown to a user while a job is active"""
    job = current_user.active_job
    if job is None:
        print("No active job")
        # todo (test code) need to correctly handle getting here without a job
        job = Job.query.get_or_404(1)
    nav_bar_title = "Job in progress"
    return render_template('oee_monitoring/jobinprogress.html',
                           job=job,
                           nav_bar_title=nav_bar_title)


@bp.route('/endjob', methods=['GET', 'POST'])
@login_required
def end_job():
    """ The page at the end of a job"""
    job = current_user.active_job
    machine = Machine.query.get_or_404(job.machine_id)
    # Sum up all of the activity
    activities = job.activities
    graph = create_machine_gantt(graph_start=job.start_time, graph_end=job.end_time, machine=machine)
    nav_bar_title = "Submit Job"
    return render_template('oee_monitoring/endjob.html',
                           nav_bar_title=nav_bar_title,
                           graph=graph)


# TODO Finish this method
@bp.route('/machineactivity', methods=['PUT'])
def machine_activity():
    """ Receives JSON data detailing a machine's activities and saves them to the database
    Example format:
    {
        "machine_number": 1,

        "activities": [
            {
                "activity_code": 1,
                "timestamp_start": 1545710000,
                "timestamp_end": 1545720000
            },
            {
              "activity_code": 1,
              "timestamp_start": 1545730000,
              "timestamp_end": 1545740000
            }
        ]
    }
    """

    json = request.get_json()

    machine_number = json['machine_number']
    machine = Machine.query.filter_by(machine_number=machine_number).first()

    # Loop through the activities in the json body and add them to the database
    for a in json['activities']:
        code = a['activity_code']
        activity_code = ActivityCode.query.filter_by(activity_code=code).first()
        timestamp_start = a['timestamp_start']
        timestamp_end = a['timestamp_end']
        new_activity = Activity(activity_code_id=activity_code.id,
                                machine_id=machine.id,
                                timestamp_start=timestamp_start,
                                timestamp_end=timestamp_end)
        db.session.add(new_activity)
        db.session.commit()

    return Response(status=200)


