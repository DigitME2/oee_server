import os
from time import time

from flask import abort, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from wtforms.validators import NoneOf, DataRequired

from app import db
from app.default.models import Activity, ActivityCode, Machine, Job, Settings, UNEXPLAINED_DOWNTIME_CODE_ID, \
    MACHINE_STATE_RUNNING, MACHINE_STATE_OFF
from app.oee_displaying.graph_helper import create_job_end_gantt
from app.oee_monitoring import bp
from app.oee_monitoring.forms import StartForm, EndForm
from app.oee_monitoring.helpers import flag_activities, get_legible_downtime_time, get_dummy_machine_activity
from app.oee_monitoring.helpers import split_activity, get_current_activity_id
from config import Config


@bp.route('/production', methods=['GET', 'POST'])
@login_required
def production():
    """ From this page, the user will be sent to a different page depending on the state of the job that is currently
    in progress"""
    active_job = Job.query.filter_by(user_id=current_user.id, active=True).first()
    # If the user doesn't have an active job, go to the start job page
    if active_job is None:
        return start_job()
    else:
        #todo need a better way of getting manual or automatic. Not feasible to put the argument in every time

        # Determine if the app is in manual or automatic mode
        # If no mode specified, default to manual
        mode = request.args.get("mode") or "manual"
        if mode == "manual":
            # Manual mode
            # Check the status of the machine to determine the state of the job
            current_machine = Machine.query.get_or_404(active_job.machine_id)
            try:
                current_activity = Activity.query.get(get_current_activity_id(current_machine.id))
                machine_state = current_activity.machine_state
            except TypeError:
                # This could be raised if there are no activities
                return manual_job_in_progress()
            if machine_state == MACHINE_STATE_RUNNING:
                return manual_job_in_progress()
            elif machine_state == MACHINE_STATE_OFF:
                return manual_job_paused()
            else:
                # This shouldn't really happen, but I think it will suffice to treat it as a pause
                current_app.logger.warn(f"Wrong machine state received: {machine_state}")
                return manual_job_paused()

        elif mode == "automatic":
            # Automatic mode
            # If the user's current job doesn't have an end time, it is in progress
            if active_job.end_time is None:
                return automatic_job_in_progress()
            else:
                return end_automatic_job()


def start_job():
    """ The page where a user with no active job is sent to"""
    form = StartForm()

    # Check to see if a machine is assigned to the device
    assigned_machine = Machine.query.filter_by(device_ip=request.remote_addr).first()
    if assigned_machine is not None:
        # Machine is not selected by user. No dropdown shown
        device_is_linked_to_machine = True
        # Remove the machine field from the form to prevent validation errors
        del form.machine
    else:
        # Machine is selected from a dropdown
        device_is_linked_to_machine = False
        # Get a list of existing machines to create form dropdown
        machine_names = []
        for m in Machine.query.filter_by(active=True).all():
            machine_names.append((str(m.id), str(m.name)))
        form.machine.choices = machine_names

    # Get a list of existing job numbers to use for form validation, preventing repeat jobs
    # job_numbers = []
    # for j in Job.query.all():
    #     job_numbers.append(str(j.job_number))
    # form.job_number.validators = [NoneOf(job_numbers, message="Job number already exists"), DataRequired()]

    if form.validate_on_submit():
        # On form submit, start a new job
        # Get the target machine from either the IP or form
        machine = assigned_machine or Machine.query.get_or_404(form.machine.data)

        # Create the new job
        start_time = time()
        job = Job(start_time=start_time,
                  user_id=current_user.id,
                  job_number=form.job_number.data,
                  planned_set_time=form.planned_set_time.data,
                  planned_cycle_time=form.planned_cycle_time.data,
                  planned_cycle_quantity=form.planned_cycle_quantity.data,
                  machine_id=machine.id,
                  active=True)
        db.session.add(job)
        db.session.commit()
        current_app.logger.debug(f"{current_user} started {job}")

        # Determine if the app is in manual or automatic mode
        # If no mode specified, default to manual
        mode = request.args.get("mode") or "manual"

        if mode == "manual":
            # Manual mode
            # Set the machine state to in-use with a kafka message
            message = f"{machine.id}_{MACHINE_STATE_RUNNING}".encode("utf-8")
            current_app.producer.send(value=message, topic=Config.KAFKA_TOPIC)
            return redirect(url_for('oee_monitoring.production'))
        else:
            # Automatic mode
            # Split the current activity so that it doesn't extend to before this job starts
            current_activity = Activity.query.get(get_current_activity_id(machine_id=machine.id))
            if current_activity is not None:
                current_app.logger.debug(f"Job started. Splitting {current_activity}")
                split_activity(activity_id=current_activity.id)
            return redirect(url_for('oee_monitoring.production'))

    nav_bar_title = "Start a new job"
    return render_template('oee_monitoring/startjob.html',
                           title="New Job",
                           form=form,
                           assigned_machine=assigned_machine,
                           device_is_linked_to_machine=device_is_linked_to_machine,
                           nav_bar_title=nav_bar_title)


def automatic_job_in_progress():
    """ The page shown to a user while a job is active"""

    current_job = Job.query.filter_by(user_id=current_user.id, active=True).first()

    form = EndForm()
    if form.validate_on_submit():
        # On form submit, give the job an end time and assign activities since start time

        # Split the current activity first
        current_activity = Activity.query.get(get_current_activity_id(machine_id=current_job.machine_id))
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
            # Set the machine state to off with a kafka message
            message = f"{current_job.machine_id}_{MACHINE_STATE_OFF}".encode("utf-8")
            current_app.producer.send(value=message, topic=Config.KAFKA_TOPIC)
            current_app.logger.info(f"Pausing {current_job}")
            return manual_job_paused()

        if action == "endJob":
            #todo put the job number in the kafka message instead of this messy method
            # while youre at it, change kafka message to be more like machine=1&state=2 instead of 1_2

            # Set the machine state to off with a kafka message
            message = f"{current_job.machine_id}_{MACHINE_STATE_OFF}".encode("utf-8")
            current_app.producer.send(value=message, topic=Config.KAFKA_TOPIC)
            current_app.logger.info(f"Ending {current_job}")
            # Give the job an end time
            current_job.end_time = time()
            # Set the job as no longer active
            current_job.active = None
            db.session.commit()

            # Get all of the machine's activity since the job started
            activities = Activity.query \
                .filter(Activity.machine_id == current_job.machine_id) \
                .filter(Activity.timestamp_start >= current_job.start_time) \
                .filter(Activity.timestamp_end <= current_job.end_time).all()
            # Flag activities that require an explanation from the operator
            flag_activities(activities, threshold=Settings.query.get_or_404(1).threshold)
            # Assign all of the activity to the current job
            for act in activities:
                current_app.logger.debug(f"Assigning {act} to {current_job}")
                act.job_id = current_job.id

        current_app.logger.debug(f"Ended {current_job}")
        return redirect(url_for('oee_monitoring.production'))

    nav_bar_title = "Job in progress"
    return render_template('oee_monitoring/manualjobinprogress.html',
                           form=form,
                           job=current_job,
                           nav_bar_title=nav_bar_title)


def manual_job_paused():
    paused_job = Job.query.filter_by(user_id=current_user.id, active=True).first()

    if request.method == "POST":
        action = request.form["action"]
        if action is None:
            abort(400)
            return

        if action == "unpause":
            # Get the reason (ie activity code) for the pause
            pause_reason = request.form["manualDowntimeReason"]

            try:
                activity_code = ActivityCode.query.get(pause_reason)
            except:
                current_app.logger.error("Could not get activity code for downtime")
                return

            # Assign the activity code to the current activity
            current_activity = Activity.query.get(get_current_activity_id(paused_job.machine_id))
            current_activity.activity_code_id = activity_code.id
            db.session.commit()

            # Set the machine state to off with a kafka message
            message = f"{paused_job.machine_id}_{MACHINE_STATE_RUNNING}".encode("utf-8")
            current_app.producer.send(value=message, topic=Config.KAFKA_TOPIC)
            current_app.logger.info(f"Unpausing {paused_job}")
            return manual_job_in_progress()

    nav_bar_title = "Job paused"
    activity_codes = ActivityCode.query.filter_by(active=True)
    return render_template('oee_monitoring/manualjobpaused.html',
                           activity_codes=activity_codes,
                           job=paused_job,
                           nav_bar_title=nav_bar_title)
