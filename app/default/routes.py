from flask import render_template, redirect, url_for, request
from flask_login import current_user, login_required
from sqlalchemy import desc

from app.admin.helpers import admin_required
from app.data_analysis.oee.availability import get_daily_machine_availability_dict, \
    get_daily_activity_duration_dict, get_daily_scheduled_runtime_dicts
from app.data_analysis.oee.performance import get_daily_performance_dict, get_daily_target_production_amount_dict
from app.data_analysis.oee.quality import get_daily_quality_dict
from app.default import bp
from app.default.helpers import get_daily_production_dict
from app.default.forms import StartJobForm, EndJobForm
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
    machines = Machine.query.all()
    start_job_form = StartJobForm()
    end_job_form = EndJobForm()
    # All activity codes
    activity_codes = ActivityCode.query.all()
    # jobs_dict =
    # Production amounts and reject amounts
    production_dict, rejects_dict = get_daily_production_dict()
    # Availability figure for each machine
    availability_dict = get_daily_machine_availability_dict(human_readable=True)
    # Scheduled uptime for each machine
    schedule_dict = get_daily_scheduled_runtime_dicts(human_readable=True)
    # Performance figure for each machine
    performance_dict = get_daily_performance_dict(human_readable=True)
    # Target production amount for each machine
    target_production_dict = get_daily_target_production_amount_dict()
    # Quality figure for each machine
    quality_dict = get_daily_quality_dict(human_readable=True)
    # Total time spent in each activity for each machine
    activity_durations_dict = get_daily_activity_duration_dict(human_readable=True)
    return render_template("default/status.html",
                           activity_codes=activity_codes,
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
                           uptime_code=Config.UPTIME_CODE_ID)


@bp.route('/machine')
@login_required
def machine():
    return render_template('default/machine.html')

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
