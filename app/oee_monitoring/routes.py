from app import db
from app.oee_monitoring import bp
from app.oee_monitoring.forms import StartForm, EndForm
from app.oee_monitoring.helpers import flag_activities, get_legible_downtime_time, assign_activity_codes
from app.default.models import Activity, ActivityCode, Machine, Job
from app.oee_displaying.graph_helper import create_shift_end_gantt
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user
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
    if current_job.end_time is not None:
        return redirect(url_for('oee_monitoring.end_job'))

    form = EndForm()
    if form.validate_on_submit():
        # Get all of the machine's activity since the job started
        activities = Activity.query \
            .filter(Activity.machine_id == current_job.machine_id) \
            .filter(Activity.timestamp_end >= current_job.start_time) \
            .filter(Activity.timestamp_start <= time()).all()
        # Assign activity codes
        assign_activity_codes(activities)
        # Flag activities that require an explanation from the operator
        flag_activities(activities)
        # Assign all of the activity to the current job
        for a in activities:
            a.job_id = current_job.id

        current_job.end_time = time()
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
    activities = current_job.activities
    # Flag activities that require an explanation
    activities = flag_activities(activities)
    if current_job is None:
        return redirect(url_for('oee_monitoring.start_job'))
    machine = Machine.query.get_or_404(current_job.machine_id)

    if request.method == "POST":
        for act in activities:
            if act.explanation_required:
                # The name of the downtime boxes is the ud_index, the value will be the activity code id selected
                act.activity_code_id = int(request.form[str(act.ud_index)])
        db.session.commit()

        # Check to see if all activities have been explained
        all_explained = True
        for act in activities:
            if act.explanation_required:
                all_explained = False
        if all_explained:
            # Set the job as no longer active
            current_job.active = None
            db.session.commit()
        return redirect(url_for('oee_monitoring.start_job'))

    for act in activities:
        if act.explanation_required:
            act.time_summary = get_legible_downtime_time(act.timestamp_start, act.timestamp_end)

    graph = create_shift_end_gantt(activities=activities,
                                   machine=machine)
    nav_bar_title = "Submit Job"
    # Give each activity its index as an attribute, so it can be retrieved easily in the jinja template
    # This must be done after creating a graph because the graph sorts the list
    for act in activities:
        act.index = activities.index(act)
    return render_template('oee_monitoring/endjob.html',
                           nav_bar_title=nav_bar_title,
                           graph=graph,
                           activity_codes=ActivityCode.query.all(),
                           activities=activities)
