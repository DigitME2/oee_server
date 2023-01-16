from datetime import datetime, timedelta, time

from flask import render_template, redirect, url_for, request
from flask_login import current_user, login_required
from sqlalchemy import desc

from app.admin.helpers import admin_required
from app.data_analysis.oee.availability import get_daily_machine_availability_dict, \
    get_daily_activity_duration_dict, get_daily_scheduled_runtime_dicts
from app.data_analysis.oee.performance import get_daily_performance_dict, get_daily_target_production_amount_dict, \
    get_daily_production_dict
from app.data_analysis.oee.quality import get_daily_quality_dict
from app.default import bp
from app.default.forms import StartJobForm, EndJobForm, EditActivityForm
from app.default.helpers import get_machine_activities, get_jobs
from app.default.models import ActivityCode, Activity, Machine
from app.login.models import User
from config import Config


@bp.route('/')
def default():
    return redirect(url_for('login.login'))


@admin_required
@bp.route('/status', methods=["GET", "POST"])
def status_page():
    """ Show today's details for all machines"""
    requested_date = request.args.get("date")
    if requested_date:
        requested_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
    else:
        requested_date = datetime.now().date()
    machines = Machine.query.all()
    start_job_form = StartJobForm()
    end_job_form = EndJobForm()
    # All activity codes
    activity_codes = ActivityCode.query.all()
    colours_dict = {}
    for ac in activity_codes:
        colours_dict[ac.id] = ac.graph_colour
    # Production amounts and reject amounts
    good_dict, rejects_dict = get_daily_production_dict(requested_date, human_readable=True)
    production_dict = {}
    for k, v in good_dict.items():
        production_dict[k] = good_dict[k] + rejects_dict[k]
    # Availability figure for each machine
    availability_dict = get_daily_machine_availability_dict(requested_date, human_readable=True)
    # Scheduled uptime for each machine
    schedule_dict = get_daily_scheduled_runtime_dicts(requested_date, human_readable=True)
    # Performance figure for each machine
    performance_dict = get_daily_performance_dict(requested_date, human_readable=True)
    # Target production amount for each machine
    target_production_dict = get_daily_target_production_amount_dict(requested_date)
    # Quality figure for each machine
    quality_dict = get_daily_quality_dict(requested_date, human_readable=True)
    # Total time spent in each activity for each machine
    activity_durations_dict = get_daily_activity_duration_dict(requested_date, human_readable=True)
    return render_template("default/status.html",
                           activity_codes=activity_codes,
                           colours_dict=colours_dict,
                           machines=machines,
                           start_job_form=start_job_form,
                           end_job_form=end_job_form,
                           current_user=current_user,
                           availability_dict=availability_dict,
                           schedule_dict=schedule_dict,
                           performance_dict=performance_dict,
                           target_production_dict=target_production_dict,
                           quality_dict=quality_dict,
                           activity_durations_dict=activity_durations_dict,
                           production_dict=production_dict,
                           rejects_dict=rejects_dict,
                           uptime_code=Config.UPTIME_CODE_ID,
                           date=requested_date)


@bp.route('/machine')
@login_required
def machine_report():
    """ Show all a user's activities and allow them to be edited """
    # TODO Finish off this page. Need to show more info for jobs and create the routes to save edits
    machine_id = request.args.get("machine_id")
    machine = Machine.query.get_or_404(machine_id)
    activity_codes = ActivityCode.query.all()
    requested_date = request.args.get("date")
    if requested_date:
        requested_date = datetime.strptime(requested_date, "%Y-%m-%d").date()
    else:
        requested_date = datetime.now().date()
    period_start = datetime.combine(date=requested_date, time=time(hour=0, minute=0, second=0, microsecond=0))
    period_end = period_start + timedelta(days=1)

    activities = get_machine_activities(machine=machine, time_start=period_start, time_end=period_end)
    activities.sort(key=lambda a: a.start_time, reverse=True)
    jobs = get_jobs(time_start=period_start, time_end=period_end, machine=machine)
    good_production_dict = {}
    reject_production_dict = {}
    for job in jobs:
        good_production_dict[job.id] = job.get_total_good_quantity()
        reject_production_dict[job.id] = job.get_total_reject_quantity()
    activity_form = EditActivityForm()
    activity_code_choices = []
    for ac in ActivityCode.query.all():
        activity_code_choices.append((str(ac.id), str(ac.short_description)))
    activity_form.activity_code.choices = activity_code_choices

    return render_template('default/machine.html',
                           title='Machine Report',
                           date=requested_date,
                           machine=machine,
                           jobs=jobs,
                           good_production_dict=good_production_dict,
                           reject_production_dict=reject_production_dict,
                           activities=activities,
                           activity_form=activity_form,
                           activity_codes=activity_codes)


# TODO This can be removed once I've finished the machine report page
@bp.route('/view_activities')
@login_required
def view_activities():
    """ Show all a user's activities and allow them to be edited """
    activity_codes = ActivityCode.query.all()
    users = User.query.all()
    if "user_id" in request.args and current_user.admin:
        user_id = request.args["user_id"]
        selected_user = User.query.get(user_id)
    else:
        user_id = current_user.id
        selected_user = User.query.get(user_id)
    activities = Activity.query \
        .filter_by(user_id=user_id) \
        .order_by(desc(Activity.start_time)) \
        .paginate(1, 50, False).items

    return render_template('default/activities.html',
                           title='Activities',
                           selected_user=selected_user,
                           users=users,
                           activities=activities,
                           activity_codes=activity_codes)
