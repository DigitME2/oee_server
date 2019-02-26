from app import db
from app.oee_monitoring import bp
from app.oee_monitoring.forms import StartForm
from app.default.models import Activity, Machine, Job
from flask import render_template, redirect, url_for, request
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


# TODO Below here is all nonsense / a work in progress
@bp.route('/machineactivity', methods=['POST'])
def machine_activity():
    """ Called to begin an activity eg uptime, downtime"""
    machine_id = request.form['machine_id']
    activity_type = request.form['activity']


    job_id = request.form['job_id']
    user_id = request.form['user_id']
    activity_code_id = request.form['activity_code_id']
    timestamp_start = time()
    new_activity = Activity(job_id=job_id, user_id=user_id, activity_code_id=activity_code_id)


@bp.route('/startactivity', methods=['POST'])
def start_activity():
    """ Called to begin an activity eg uptime, downtime"""
    job_id = request.form['job_id']
    user_id = request.form['user_id']
    activity_code_id = request.form['activity_code_id']
    timestamp_start = time()

    new_activity = Activity(job_id=job_id, user_id=user_id, activity_code_id=activity_code_id)
