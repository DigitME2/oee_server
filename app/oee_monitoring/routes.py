from app import db
from app.oee_monitoring import bp
from app.oee_monitoring.forms import StartForm, EndForm, CompleteJobForm
from app.default.models import Activity, ActivityCode, Machine, Job
from flask import render_template, redirect, url_for, request, Response
from flask_login import login_required, current_user
from app.oee_displaying.graph_helper import create_machine_gantt
from wtforms.validators import NoneOf

from time import time


@bp.route('/startjob', methods=['GET', 'POST'])
@login_required
def start_job():
    """ The page where a user will start a job"""

    # Redirect if user has an active job
    if Job.query.filter_by(user_id=current_user.id, active=True).first() is not None:
        return redirect(url_for('oee_monitoring.job_in_progress'))
    form = StartForm()

    # Get a list of existing job numbers to send to form for validation
    machine_numbers = []
    # for m in Machine.query.all():
    #     machine_numbers.append(str(m.machine_number))
    job_numbers = []
    for j in Job.query.all():
        job_numbers.append(str(j.job_number))
    # Get a list of existing machines to send to form for validation
    form = StartForm()
    # form.job_number.validators.append(NoneOf(job_numbers))
    # form.machine_number.choices = machine_numbers

    if form.validate_on_submit():
        job_number = form.job_number.data
        # TODO check the machine exists
        machine_number = form.machine_number.data
        machine = Machine.query.filter_by(machine_number=machine_number).first()
        start_time = time()
        job = Job(start_time=start_time,
                  user_id=current_user.id,
                  job_number=job_number,
                  machine_id=machine.id,
                  active=True)
        db.session.add(job)
        db.session.commit()
        return redirect(url_for('oee_monitoring.job_in_progress'))
    nav_bar_title = "Start a new job"
    return render_template('oee_monitoring/startjob.html',
                           title="New Job",
                           form=form,
                           nav_bar_title=nav_bar_title)


@bp.route('/jobinprogress', methods=['GET', 'POST'])
@login_required
def job_in_progress():
    """ The page shown to a user while a job is active"""
    job = Job.query.filter_by(user_id=current_user.id, active=True).first()
    if job is None:
        return redirect(url_for('oee_monitoring.start_job'))

    form = EndForm()
    if form.validate_on_submit():
        return redirect(url_for('oee_monitoring.end_job'))

    nav_bar_title = "Job in progress"
    return render_template('oee_monitoring/jobinprogress.html',
                           form=form,
                           job=job,
                           nav_bar_title=nav_bar_title)


@bp.route('/endjob', methods=['GET', 'POST'])
@login_required
def end_job():
    """ The page at the end of a job
    This shows the user a summary of the machine's activities and requests reasons for certain activities"""

    job = Job.query.filter_by(user_id=current_user.id, active=True).first()
    if job is None:
        return redirect(url_for('oee_monitoring.start_job'))

    form = CompleteJobForm()
    if form.validate_on_submit():
        job.active = None
        job.end_time = time()
        db.session.commit()
        return redirect(url_for('oee_monitoring.start_job'))
    machine = Machine.query.get_or_404(job.machine_id)
    # Sum up all of the activity
    activities = job.activities
    graph = create_machine_gantt(graph_start=job.start_time, graph_end=time(), machine=machine)
    nav_bar_title = "Submit Job"
    return render_template('oee_monitoring/endjob.html',
                           nav_bar_title=nav_bar_title,
                           form=form,
                           graph=graph)


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


