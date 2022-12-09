from datetime import datetime, time, timedelta

from flask import render_template, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from sqlalchemy import desc

from app.data_analysis.oee.availability import get_machine_availability, get_daily_machine_availability_dict, \
    get_activity_duration_dict, get_daily_activity_duration_dict
from app.data_analysis.oee.performance import get_daily_performance_dict, get_daily_target_production_amount_dict
from app.data_analysis.oee.quality import get_daily_quality_dict
from app.default import bp
from app.default.db_helpers import create_all_scheduled_activities, get_daily_production_dict
from app.default.models import ActivityCode, Activity, Machine, ProductionQuantity
from app.login.models import User
from app.visualisation.helpers import get_machine_status
from config import Config


@bp.route('/')
def default():
    return redirect(url_for('login.login'))


@bp.route('/status')
def status_page():
    machines = Machine.query.all()
    activity_codes = ActivityCode.query.all()
    production_dict, rejects_dict = get_daily_production_dict()
    availability_dict = get_daily_machine_availability_dict(human_readable=True)
    performance_dict = get_daily_performance_dict(human_readable=True)
    target_production_dict = get_daily_target_production_amount_dict()
    quality_dict = get_daily_quality_dict(human_readable=True)
    activity_durations_dict = get_daily_activity_duration_dict(human_readable=True)
    return render_template("default/status.html",
                           activity_codes=activity_codes,
                           machines=machines,
                           current_user=current_user,
                           availability_dict=availability_dict,
                           performance_dict=performance_dict,
                           target_production_dict=target_production_dict,
                           quality_dict=quality_dict,
                           activity_durations_dict=activity_durations_dict,
                           production_dict=production_dict,
                           rejects_dict=rejects_dict,
                           uptime_code=Config.UPTIME_CODE_ID)


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
        .order_by(desc(Activity.time_start)) \
        .paginate(1, 50, False).items

    return render_template('default/activities.html',
                           title='Activities',
                           selected_user=selected_user,
                           users=users,
                           activities=activities,
                           activity_codes=activity_codes)


@bp.route('/run_schedule', methods=['POST'])
def create_scheduled_activities_route():
    if "date" in request.args:
        dt = datetime.strptime(request.args['date'], '%d-%m-%y').date()
    else:
        dt = datetime.now().date()

    create_all_scheduled_activities(create_date=dt)
    return jsonify({'success': True}), 200, {'ContentType': 'application/json'}
