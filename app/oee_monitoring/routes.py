from app import db
from app.oee_monitoring import bp
from app.oee_monitoring.forms import StartForm
from app.oee_monitoring.models import Machine, Job, Activity, ActivityCode
from datetime import datetime
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.oee_monitoring.graph_helper import create_machine_gantt, create_all_machines_gantt

from time import time



@login_required
@bp.route('/home')
def home():
    """ The default page for a logged-in user"""
    db.create_all()
    return render_template('oee_monitoring/home.html')


@login_required
@bp.route('/adminhome', methods=['GET'])
def admin_home():
    """ The default page for a logged-in user"""
    return render_template('oee_monitoring/adminhome.html')


@login_required
@bp.route('/startjob', methods=['GET', 'POST'])
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


@login_required
@bp.route('/jobinprogress', methods=['GET', 'POST'])
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


@login_required
@bp.route('/endjob', methods=['GET', 'POST'])
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


@login_required
@bp.route('/machine')
def machine():
    """ The page showing the OEE of a machine and reasons for downtime"""
    target_machine = Machine.query.get_or_404(request.args.get('id'))

    start = int(request.args.get('start'))
    end = int(request.args.get('end'))

    # start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()  # = 1545728400.0
    # end = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()  # = 1545757200.0

    graph = create_machine_gantt(graph_start=start, graph_end=end, machine=target_machine)
    nav_bar_title = "{machine_name} OEE | {start} - {end}".format(
        machine_name=target_machine.name,
        start=datetime.fromtimestamp(start).strftime("%a %d %b %Y (%H:%M"),
        end=datetime.fromtimestamp(end).strftime("%H:%M)"))
    return render_template('oee_monitoring/machine.html',
                           graph=graph,
                           title=target_machine.name,
                           nav_bar_title=nav_bar_title)


@bp.route('/allmachines', methods=['GET', 'POST'])
def all_machines():
    """ The page showing the OEE of all the machines"""
    try:
        # Get the values for the start and end time of the graph from the url
        start = int(request.args.get('start'))
        end = int(request.args.get('end'))
    except TypeError:  # Happens when no parameters in url
        # todo handle this exception properly (test code)
        start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()  # = 1545728400.0
        end = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()  # = 1545757200.0

    graph = create_all_machines_gantt(graph_start=start, graph_end=end)
    return render_template('oee_monitoring/allmachines.html', graph=graph)


