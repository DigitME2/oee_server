import json
import time
from datetime import datetime, timedelta

from flask import current_app, render_template, redirect, url_for, request
from flask_login import current_user, login_required

from app import db
from app.default import bp
from app.default.models import Machine, ScheduledActivity
from config import Config


@bp.route('/')
def default():
    return redirect(url_for('login.login'))


@bp.route('/index')
@login_required
def index():
    """ The default page """
    if current_user.is_authenticated:
        user = {'username': current_user.username, 'id': current_user.id}
    else:
        user = {'username': "nobody"}
    return render_template('default/index.html', title='Index', user=user)


@bp.route('/run_schedule', methods=['POST'])
def create_scheduled_activities():

    if "date" in request.args:
        dt = datetime.strptime(request.args['date'], '%d-%m-%y')
    else:
        dt = datetime.now()

    current_app.logger.info(f"Creating Scheduled Activities for {dt.strftime('%d-%m-%y')}")
    last_midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight = last_midnight + timedelta(days=1)

    for machine in Machine.query.all():

        # Check to see if any scheduled activities already exist for today and skip if any exist
        existing_activities = ScheduledActivity.query \
            .filter(ScheduledActivity.machine_id == machine.id) \
            .filter(ScheduledActivity.timestamp_start >= last_midnight.timestamp()) \
            .filter(ScheduledActivity.timestamp_end <= next_midnight.timestamp()).all()
        if len(existing_activities) > 0:
            current_app.logger.warning(f"Scheduled activities already exist today for {machine} Skipping...")
            continue

        # Get the shift for this day of the week
        weekday = dt.weekday()
        current_app.logger.debug(f"Weekday: {weekday}")
        shift = machine.schedule.get_shifts().get(weekday)

        # Create datetime objects with today's date and the times from the schedule table
        shift_start = datetime.combine(dt, datetime.strptime(shift[0], "%H%M").timetz())
        shift_end = datetime.combine(dt, datetime.strptime(shift[1], "%H%M").timetz())

        current_app.logger.info(f"{machine} \nShift start: {shift_start} \nShift end: {shift_end}")

        if shift_start != last_midnight:  # Skip making this activity if it will be 0 length
            before_shift = ScheduledActivity(machine_id=machine.id,
                                             scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                             timestamp_start=last_midnight.timestamp(),
                                             timestamp_end=shift_start.timestamp())
            db.session.add(before_shift)

        if shift_start != shift_end:  # Skip making this activity if it will be 0 length
            during_shift = ScheduledActivity(machine_id=machine.id,
                                             scheduled_machine_state=Config.MACHINE_STATE_RUNNING,
                                             timestamp_start=shift_start.timestamp(),
                                             timestamp_end=shift_end.timestamp())
            db.session.add(during_shift)

        if shift_end != next_midnight:  # Skip making this activity if it will be 0 length
            after_shift = ScheduledActivity(machine_id=machine.id,
                                            scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                            timestamp_start=shift_end.timestamp(),
                                            timestamp_end=next_midnight.timestamp())
            db.session.add(after_shift)

        db.session.commit()

    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@bp.route('/create_fake_data', methods=['POST'])
def create_fake_data():
    """Create fake data if in demo mode"""
    if not Config.DEMO_MODE:
        print("Cannot fake data: App is not in demo mode.")
        return
    from app.testing.machine_simulator import simulate_machines
    simulate_machines()
