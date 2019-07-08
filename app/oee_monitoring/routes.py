import os
from time import time

from flask import abort, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from wtforms.validators import NoneOf, DataRequired

from app import db
from app.default.models import Activity, ActivityCode, Machine, Job, Settings, UNEXPLAINED_DOWNTIME_CODE_ID, \
    MACHINE_STATE_RUNNING, MACHINE_STATE_IDLE
from app.oee_displaying.graph_helper import create_job_end_gantt
from app.oee_monitoring import bp
from app.oee_monitoring.forms import StartForm, EndForm
from app.oee_monitoring.helpers import flag_activities, get_legible_downtime_time, get_dummy_machine_activity
from app.oee_monitoring.helpers import split_activity, get_current_activity
from config import Config


@bp.route('/production-auto', methods=['GET', 'POST'])
@login_required
def automatic_production():
    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()
    # If the user doesn't have an active job, go to the start job page
    if current_job is None:
        return start_automatic_job()
    else:
        # If the user's current job doesn't have an end time, it is in progress
        if current_job.end_time is None:
            return automatic_job_in_progress()
        else:
            return end_automatic_job()


@bp.route('/production-manual', methods=['GET', 'POST'])
@login_required
def manual_production():
    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()
    # If the user doesn't have an active job, go to the start job page
    if current_job is None:
        return start_manual_job()
    # If the user has a job, check the state of the machine
    else:
        current_machine = Machine.query.get_or_404(current_job.machine_id)
        machine_state = get_current_activity(current_machine.id).machine_state
        if machine_state == MACHINE_STATE_RUNNING:
            return manual_job_in_progress()
        elif machine_state == MACHINE_STATE_IDLE:
            return manual_job_paused()
        else:
            # This shouldn't really happen, but I think it will suffice to treat it as a pause
            current_app.logger.warn("Recorded machine as off while user logged on")
            return manual_job_paused()


def start_automatic_job():
    """ The page where a user will start a job"""

    form = StartForm()
    # Get a list of existing machines to create form dropdown
    machine_names = []
    for m in Machine.query.filter_by(active=True).all():
        machine_names.append((str(m.id), str(m.name)))
    form.machine.choices = machine_names
    # Get a list of existing job numbers to use for form validation
    job_numbers = []
    for j in Job.query.all():
        job_numbers.append(str(j.job_number))
    form.job_number.validators = [NoneOf(job_numbers, message="Job number already exists"), DataRequired()]

    if form.validate_on_submit():
        # On form submit, start a new job
        machine = Machine.query.get_or_404(form.machine.data)

        # Create the new job
        start_time = time()
        job = Job(start_time=start_time,
                  user_id=current_user.id,
                  job_number=form.job_number.data,
                  machine_id=machine.id,
                  active=True)
        db.session.add(job)
        db.session.commit()
        current_app.logger.debug(f"{current_user} started {job}")

        # Split the current activity so that it doesn't extend to before this job starts
        current_activity = get_current_activity(machine_id=machine.id)
        if current_activity is not None:
            current_app.logger.debug(f"Job started. Splitting {current_activity}")
            split_activity(activity_id=current_activity.id)

        return redirect(url_for('oee_monitoring.automatic_production'))
    nav_bar_title = "Start a new job"
    return render_template('oee_monitoring/startjob.html',
                           title="New Job",
                           form=form,
                           nav_bar_title=nav_bar_title)


def automatic_job_in_progress():
    """ The page shown to a user while a job is active"""

    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()

    form = EndForm()
    if form.validate_on_submit():
        # On form submit, give the job an end time and assign activities since start time

        # Split the current activity first
        current_activity = get_current_activity(machine_id=current_job.machine_id)
        if current_activity is not None:
            current_app.logger.debug(f"Job ended. Splitting {current_activity}")
            split_activity(activity_id=current_activity.id)

        # Give the job an end time
        current_job.end_time = time()

        # Get all of the machine's activity since the job started
        activities = Activity.query \
            .filter(Activity.machine_id == current_job.machine_id) \
            .filter(Activity.timestamp_start >= current_job.start_time) \
            .filter(Activity.timestamp_end <= current_job.end_time).all()
        # Flag activities that require an explanation from the operator
        flag_activities(activities, threshold=Settings.query.get_or_404(1).threshold)
        # Assign all of the activity to the current job
        for a in activities:
            current_app.logger.debug(f"Assigning {a} to {current_job}")
            a.job_id = current_job.id

        # If in demo mode, change the job times and create fake activities
        if os.environ.get('DEMO_MODE') == 'True':
            current_app.logger.info("DEMO_MODE: Creating fake machine activity")
            current_job.start_time = current_job.end_time - 10800
            db.session.add(current_job)
            activities = get_dummy_machine_activity(timestamp_end=current_job.end_time,
                                                    timestamp_start=current_job.start_time,
                                                    job_id=current_job.id,
                                                    machine_id=current_job.machine_id)
            for act in activities:
                db.session.add(act)
        # end debug code

        db.session.commit()
        current_app.logger.debug(f"Ended {current_job}")
        return redirect(url_for('oee_monitoring.automatic_production'))

    nav_bar_title = "Job in progress"
    return render_template('oee_monitoring/jobinprogress.html',
                           form=form,
                           job=current_job,
                           nav_bar_title=nav_bar_title)


def end_automatic_job():
    """ The page at the end of a job
    This shows the user a summary of the machine's activities and requests reasons for certain activities"""


    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()
    activities = current_job.activities
    # Flag activities that require an explanation
    explanation_threshold = Settings.query.get_or_404(1).threshold
    activities = flag_activities(activities, explanation_threshold)
    if current_job is None:
        return redirect(url_for('oee_monitoring.automatic_production'))

    if request.method == "POST":
        # All POST requests will be an attempt to complete the job

        # The dropdown boxes selected by the operator have a ud_index, that is, the index to which activity it is
        # referring to. So if ud_index=1 then that refers to the first activity that requires an explanation
        for act in activities:
            if act.explanation_required:
                # The name of the downtime boxes is the ud_index, the value of the box is the activity code id selected
                act.activity_code_id = int(request.form[str(act.ud_index)])
                current_app.logger.debug(f"Setting {act} to ActivityCode ID {act.activity_code_id}")
                # If the activity is still saved as unexplained, don't remove the explanation_required flag
                if act.activity_code_id != UNEXPLAINED_DOWNTIME_CODE_ID:
                    act.explanation_required = False
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
            current_app.logger.debug(f"{current_user} completed {current_job}")
            return redirect(url_for('oee_monitoring.automatic_production'))
        else:
            current_app.logger.debug(f"Job not completed, unexplained activities still exist")
            flash("Please complete all jobs")
            return redirect(url_for('oee_monitoring.automatic_production'))

    for act in activities:
        if act.explanation_required:
            act.time_summary = get_legible_downtime_time(act.timestamp_start, act.timestamp_end)

    graph = create_job_end_gantt(job=current_job)
    nav_bar_title = "Submit Job"
    # Give each activity its index as an attribute, so it can be retrieved easily in the jinja template
    # This must be done after creating a graph because the graph sorts the list
    for act in activities:
        act.index = activities.index(act)
    # Create a dictionary of colours for javascript to change graph colours from the dropdown selection
    colours = {}
    for ac in ActivityCode.query.all():
        colours[ac.id] = ac.graph_colour
    # Filter out activity codes that aren't in use
    activity_codes = ActivityCode.query.filter_by(active=True)
    return render_template('oee_monitoring/endjob.html',
                           nav_bar_title=nav_bar_title,
                           graph=graph,
                           activity_codes=activity_codes,
                           activities=activities,
                           colours=colours)


def start_manual_job():
    """ The page where a user will start a manual job (one that requires the user to enter machine state)"""

    form = StartForm()
    # Get a list of existing machines to create form dropdown
    machine_names = []
    for m in Machine.query.filter_by(active=True).all():
        machine_names.append((str(m.id), str(m.name)))
    form.machine.choices = machine_names
    # Get a list of existing job numbers to use for form validation
    job_numbers = []
    for j in Job.query.all():
        job_numbers.append(str(j.job_number))
    form.job_number.validators = [NoneOf(job_numbers, message="Job number already exists"), DataRequired()]

    if form.validate_on_submit():
        # On form submit, start a new job
        machine = Machine.query.get_or_404(form.machine.data)

        # Set the machine state to in-use with a kafka message
        message = f"{machine.id}_{MACHINE_STATE_RUNNING}".encode("utf-8")
        current_app.producer.send(value=message, topic=Config.KAFKA_TOPIC)

        # Create the new job
        start_time = time()
        job = Job(start_time=start_time,
                  user_id=current_user.id,
                  job_number=form.job_number.data,
                  machine_id=machine.id,
                  active=True)
        db.session.add(job)
        db.session.commit()
        current_app.logger.debug(f"{current_user} started {job}")

        return redirect(url_for('oee_monitoring.manual_production'))
    nav_bar_title = "Start a new job"
    return render_template('oee_monitoring/startjob.html',
                           title="New Job",
                           form=form,
                           nav_bar_title=nav_bar_title)


def manual_job_in_progress():
    """ The page shown to a user while a job is active. This handles jobs where the user is required to manually
    enter the states of the machine"""

    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()

    form = EndForm()

    if request.method == "POST":
        action = request.form["action"]
        if action is None:
            abort(400)
            return

        if action == "pause":
            # Set the machine state to idle with a kafka message
            message = f"{current_job.machine_id}_{MACHINE_STATE_IDLE}".encode("utf-8")
            current_app.producer.send(value=message, topic=Config.KAFKA_TOPIC)
            current_app.logger.info(f"Pausing {current_job}")
            return manual_job_paused()

        if action == "endJob":
            pass

    if form.validate_on_submit():
        # On form submit, give the job an end time and assign activities since start time

        # Split the current activity first
        current_activity = get_current_activity(machine_id=current_job.machine_id)
        if current_activity is not None:
            current_app.logger.debug(f"Job ended. Splitting {current_activity}")
            split_activity(activity_id=current_activity.id)

        # Give the job an end time
        current_job.end_time = time()

        # Get all of the machine's activity since the job started
        activities = Activity.query \
            .filter(Activity.machine_id == current_job.machine_id) \
            .filter(Activity.timestamp_start >= current_job.start_time) \
            .filter(Activity.timestamp_end <= current_job.end_time).all()
        # Flag activities that require an explanation from the operator
        flag_activities(activities, threshold=Settings.query.get_or_404(1).threshold)
        # Assign all of the activity to the current job
        for a in activities:
            current_app.logger.debug(f"Assigning {a} to {current_job}")
            a.job_id = current_job.id

        # If in demo mode, change the job times and create fake activities
        if os.environ.get('DEMO_MODE') == 'True':
            current_app.logger.info("DEMO_MODE: Creating fake machine activity")
            current_job.start_time = current_job.end_time - 10800
            db.session.add(current_job)
            activities = get_dummy_machine_activity(timestamp_end=current_job.end_time,
                                                    timestamp_start=current_job.start_time,
                                                    job_id=current_job.id,
                                                    machine_id=current_job.machine_id)
            for act in activities:
                db.session.add(act)
        # end debug code

        db.session.commit()
        current_app.logger.debug(f"Ended {current_job}")
        return redirect(url_for('oee_monitoring.manual_production'))

    nav_bar_title = "Job in progress"
    return render_template('oee_monitoring/manualjobinprogress.html',
                           form=form,
                           job=current_job,
                           nav_bar_title=nav_bar_title)


def manual_job_paused():
    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()

    if request.method == "POST":
        action = request.form["action"]
        if action is None:
            abort(400)
            return

        if action == "unpause":
            # Get the reason (ie activity code) for the pause
            # todo

            # Assign the activity code to the activity
            # todo

            # Set the machine state to idle with a kafka message
            message = f"{current_job.machine_id}_{MACHINE_STATE_RUNNING}".encode("utf-8")
            current_app.producer.send(value=message, topic=Config.KAFKA_TOPIC)
            current_app.logger.info(f"Unpausing {current_job}")
            return manual_job_in_progress()

    nav_bar_title = "Job paused"
    return render_template('oee_monitoring/manualjobpaused.html',
                           job=current_job,
                           nav_bar_title=nav_bar_title)


def pause_job(machine_id):
    # Set the machine state to idle with a kafka message
    message = f"{machine_id}_{MACHINE_STATE_IDLE}".encode("utf-8")
    current_app.producer.send(value=message, topic=Config.KAFKA_TOPIC)
    pass


def unpause_job():
    pass
