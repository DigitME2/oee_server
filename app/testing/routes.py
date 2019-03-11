from datetime import datetime
from random import randrange

from flask import render_template
from flask_login import current_user

from app import db
from app.testing import bp
from app.default.models import Machine, ActivityCode, Job, Activity, UPTIME_CODE, UNEXPLAINED_DOWNTIME_CODE
from app.login.models import User
from app.testing.forms import TestForm, NewBatchForm

@bp.route('/test')
def test():
    form = TestForm()
    return render_template('testing/test.html', form=form)


@bp.route('/newbatch', methods=['GET', 'POST'])
def new_batch():
    """The page to create a new batch"""
    form = NewBatchForm()
    # Create list of part names to fill the part-type selection box
    part_names = [1, 2, 3]

    form.part_type.choices = part_names

    # Create a new batch, and new parts when form is submitted

    nav_bar_title = "Create new batch"
    return render_template('testing/newbatch.html', form=form,
                           nav_bar_title=nav_bar_title)


@bp.route('/createdata')
def create_data():
    """ Creates fake data to use for testing purposes"""
    db.create_all()

    unexplainedcode = ActivityCode(code=UNEXPLAINED_DOWNTIME_CODE, short_description='unexplained')
    db.session.add(unexplainedcode)
    uptimecode = ActivityCode(code=UPTIME_CODE, short_description='uptime')
    db.session.add(uptimecode)
    error1code = ActivityCode(code=2, short_description='error1')
    db.session.add(error1code)
    error2code = ActivityCode(code=3, short_description='error2')
    db.session.add(error2code)
    error3code = ActivityCode(code=4, short_description='error3')
    db.session.add(error3code)
    db.session.commit()

    for i in range(0, 5):

        user = User(username="user"+str(i))
        user.set_password("password")

        new_machine = Machine(machine_number=str(i+1), name="Bridgeport " + str(i+1))
        db.session.add(new_machine)
        db.session.commit()

        job_start = datetime(year=2018, month=12, day=25, hour=9, minute=0)
        job_end = datetime(year=2018, month=12, day=25, hour=17, minute=0)
        new_job = Job(start_time=job_start.timestamp(),
                      end_time=job_end.timestamp(),
                      job_number=str(i),
                      machine_id=i,
                      user_id=i)

        db.session.add(new_job)
        db.session.commit()

        start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()
        finish = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()
        time = start
        while time <= finish:
            uptime_activity = Activity(machine_id=i,
                                       timestamp_start=time,
                                       machine_state=1,
                                       activity_code=UPTIME_CODE)
            time += randrange(600, 14400)
            uptime_activity.timestamp_end = time

            machine_state = randrange(0, 3)
            if machine_state == 1:
                machine_state = 0
            downtime_activity = Activity(machine_id=i,
                                         timestamp_start=time,
                                         machine_state=machine_state,
                                         activity_code=randrange(2, 5))
            time += randrange(60, 1200)
            downtime_activity.timestamp_end = time
            db.session.add(uptime_activity)
            db.session.add(downtime_activity)
            db.session.commit()

    # an active job for the current user
    job_start = datetime(year=2018, month=12, day=26, hour=9, minute=0)
    new_job = Job(start_time=job_start.timestamp(), job_number=str(i+1),
                  machine_id=i+1, user_id=current_user.id)
    current_user.active_job = new_job
    db.session.add(new_job)
    db.session.commit()

    return "Created fake data"
