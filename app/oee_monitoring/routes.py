from app import db
from app.oee_monitoring import bp
from app.oee_monitoring.forms import StartForm, EndForm, CompleteJobForm
from app.default.models import Activity, Machine, Job
from flask import render_template, redirect, url_for
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
    # Get a list of existing machines to create form dropdown
    machine_numbers = []
    for m in Machine.query.all():
        machine_numbers.append((str(m.machine_number), str(m.machine_number)))
    form.machine_number.choices = machine_numbers
    # Get a list of existing job numbers to send to form for validation
    job_numbers = []
    for j in Job.query.all():
        job_numbers.append(str(j.job_number))
    form.job_number.validators.append(NoneOf(job_numbers))

    if form.validate_on_submit():
        machine = Machine.query.filter_by(machine_number=form.machine_number.data).first()
        start_time = time()
        job = Job(start_time=start_time,
                  user_id=current_user.id,
                  job_number=form.job_number.data,
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
    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()
    if current_job is None:
        return redirect(url_for('oee_monitoring.start_job'))

    form = EndForm()
    if form.validate_on_submit():
        # Get all of the machine's activity since the job started
        activities = Activity.query \
            .filter(Activity.machine_id == current_job.machine_id) \
            .filter(Activity.timestamp_end >= current_job.start_time) \
            .filter(Activity.timestamp_start <= time()).all()
        # Assign all of the activity to the current job
        for a in activities:
            a.job_id = current_job.id
        db.session.commit()
        return redirect(url_for('oee_monitoring.end_job'))

    nav_bar_title = "Job in progress"
    return render_template('oee_monitoring/jobinprogress.html',
                           form=form,
                           job=current_job,
                           nav_bar_title=nav_bar_title)


@bp.route('/endjob', methods=['GET', 'POST'])
@login_required
def end_job():
    """ The page at the end of a job
    This shows the user a summary of the machine's activities and requests reasons for certain activities"""

    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()
    if current_job is None:
        return redirect(url_for('oee_monitoring.start_job'))
    machine = Machine.query.get_or_404(current_job.machine_id)

    # TODO Get a list of activities that require an explanation from the operator

    form = CompleteJobForm()
    if form.validate_on_submit():
        current_job.active = None
        current_job.end_time = time()
        db.session.commit()
        return redirect(url_for('oee_monitoring.start_job'))

    graph = create_machine_gantt(graph_start=current_job.start_time, graph_end=time(), machine=machine)
    nav_bar_title = "Submit Job"
    return render_template('oee_monitoring/endjob.html',
                           nav_bar_title=nav_bar_title,
                           form=form,
                           graph=graph)


def get_flagged_activities(activities):
    """ Filters a list of activities and returns a list that require explanation
    from the operator"""
