from datetime import datetime

from flask import render_template, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from sqlalchemy import desc

from app.default import bp
from app.default.db_helpers import create_all_scheduled_activities
from app.default.models import ActivityCode, Activity
from app.login.models import User


@bp.route('/')
def default():
    return redirect(url_for('login.login'))


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
