import json
from datetime import datetime, timedelta

from flask import current_app, render_template, redirect, url_for
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


@bp.route('/run_schedule', methods=['POST', 'GET'])  # todo remove 'get' after testing
def create_scheduled_activities():
    current_app.logger.info(f"Creating Scheduled Activities")
    last_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    next_midnight = last_midnight + timedelta(days=1)
    for machine in Machine.query.all():
        # TODO dont make a schedule on days where shift starts and ends at midnight
        current_app.logger.debug(f"Creating Scheduled Activities for {machine}")

        # Check to see if any scheduled activities already exist for today
        existing_activities = ScheduledActivity.query \
            .filter(ScheduledActivity.machine_id == machine.id) \
            .filter(ScheduledActivity.timestamp_start > last_midnight.timestamp()) \
            .filter(ScheduledActivity.timestamp_end < next_midnight.timestamp()).all()

        if len(existing_activities) > 0:
            current_app.logger.warning(f"Scheduled activities already exist today for {machine} Skipping...")
            continue

        sched = machine.schedule

        for shift in sched.get_shifts():
            # Create datetime objects with today's date and the times from the schedule table
            shift_start = datetime.combine(datetime.now(), datetime.strptime(shift[0], "%H%M").timetz())
            shift_end = datetime.combine(datetime.now(), datetime.strptime(shift[1], "%H%M").timetz())

            # noinspection PyArgumentList
            before_shift = ScheduledActivity(machine_id=machine.id,
                                             scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                             timestamp_start=last_midnight.timestamp(),
                                             timestamp_end=shift_start.timestamp())

            # noinspection PyArgumentList
            during_shift = ScheduledActivity(machine_id=machine.id,
                                             scheduled_machine_state=Config.MACHINE_STATE_RUNNING,
                                             timestamp_start=shift_start.timestamp(),
                                             timestamp_end=shift_end.timestamp())

            # noinspection PyArgumentList
            after_shift = ScheduledActivity(machine_id=machine.id,
                                            scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                            timestamp_start=shift_end.timestamp(),
                                            timestamp_end=next_midnight.timestamp())

            db.session.add(before_shift)
            db.session.add(during_shift)
            db.session.add(after_shift)
            db.session.commit()
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
