from datetime import datetime
from random import randrange

from flask import render_template
from flask_login import current_user

from app import db
from app.testing import bp
from app.default.models import Machine, ActivityCode, Job, Activity


@bp.route('/test')
def test():

    machine = Machine.query.first()
    time1 = datetime(year=2018, month=12, day=25, hour=9, minute=0)
    time2 = datetime(year=2018, month=12, day=25, hour=17, minute=0)

    return render_template('testing/test.html')


@bp.route('/createdata')
def create_data():
    """ Create fake random database data for testing"""
    uptimecode = ActivityCode(activity_code=1, description='uptime')
    db.session.add(uptimecode)
    error1code = ActivityCode(activity_code=2, description='error1')
    db.session.add(error1code)
    error2code = ActivityCode(activity_code=3, description='error2')
    db.session.add(error2code)
    error3code = ActivityCode(activity_code=4, description='error3')
    db.session.add(error3code)
    db.session.commit()

    for i in range(0, 5):

        new_machine = Machine(name="machine " + str(i))
        db.session.add(new_machine)
        db.session.commit()

        job_start = datetime(year=2018, month=12, day=25, hour=9, minute=0)
        job_end = datetime(year=2018, month=12, day=25, hour=17, minute=0)
        new_job = Job(start_time=job_start.timestamp(),
                      end_time=job_end.timestamp(),
                      job_number=str(i),
                      machine_id=i,
                      user_id=current_user.id)

        db.session.add(new_job)
        db.session.commit()

        start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()
        finish = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()
        time = start
        while time <= finish:
            uptime_activity = Activity(user_id=1,
                                       machine_id=i,
                                       timestamp_start=time,
                                       activity_code_id=1)
            time += randrange(600, 14400)
            uptime_activity.timestamp_end = time

            downtime_activity = Activity(user_id=1,
                                         machine_id=i,
                                         timestamp_start=time,
                                         activity_code_id=randrange(2, 5))
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