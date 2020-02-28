import time
import os
from datetime import datetime
from datetime import datetime
from random import randrange

import pandas as pd
from app import db
from app.export.helpers import *
from app.login.models import User
from app.default.models import *
from app.default.db_helpers import get_machines_last_job
from app.oee_displaying.graph_helper import create_downtime_pie
from app.login.models import User
from app.testing import bp
from config import Config
from flask import render_template, request, jsonify, abort, current_app, send_file, session
from flask_login import current_user


@bp.route('/test')
def test():
    #create_users_csv(time_start=1572268033, time_end=1572280302)

    get_machines_last_job(1)
    return "test"

@bp.route('/test1')
def test1():

    return "Create scheduled activities"


def sort_activities(act):
    return act.activity_code.id


#@bp.route('/createdata')
def create_data():
    """ Creates fake data to use for testing purposes"""
    db.create_all()

    # unexplained and uptime are created on database initialisation
    # unexplainedcode = ActivityCode(id=UNEXPLAINED_DOWNTIME_CODE_ID, code="EX", short_description='unexplained',
    #                                graph_colour='rgb(178,34,34)')
    # db.session.add(unexplainedcode)
    # uptimecode = ActivityCode(id=UPTIME_CODE_ID, code="UP", short_description='uptime', graph_colour='rgb(0, 255, 128)')
    # db.session.add(uptimecode)
    error1code = ActivityCode(id=2, code="ER1", short_description='error1', graph_colour='rgb(255,64,0)')
    db.session.add(error1code)
    error2code = ActivityCode(id=3, code="ER2", short_description='error2', graph_colour='rgb(255,0,0)')
    db.session.add(error2code)
    error3code = ActivityCode(id=4, code="ER3", short_description='error3', graph_colour='rgb(255,255,0)')
    db.session.add(error3code)
    db.session.commit()



    for i in range(1, 6):
        user = User(username="user"+str(i))
        user.set_password("password")

        # First machine is created automatically
        if i != 1:
            new_machine = Machine(name="Machine " + str(i))
            db.session.add(new_machine)
            db.session.commit()

        job_start = datetime(year=2018, month=12, day=25, hour=9, minute=0)
        job_end = datetime(year=2018, month=12, day=25, hour=17, minute=0)


        start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()
        finish = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()
        time = start
        current_job = None
        while time <= finish:
            # chance of changing active job
            if randrange(0, 3) > 1:
                current_job = change_job(current_job, time, i)
            if current_job is None:
                job_id = None
            else:
                job_id = current_job.id
            uptime_activity = Activity(machine_id=i,
                                       timestamp_start=time,
                                       machine_state=1,
                                       activity_code_id=UPTIME_CODE_ID,
                                       job_id=job_id)
            time += randrange(400, 10000)
            uptime_activity.timestamp_end = time

            machine_state = randrange(0, 3)
            if machine_state == 1:
                machine_state = 0
            downtime_activity = Activity(machine_id=i,
                                         timestamp_start=time,
                                         machine_state=machine_state,
                                         activity_code_id=randrange(2, 5),
                                         job_id=job_id)
            time += randrange(60, 2000)
            downtime_activity.timestamp_end = time
            db.session.add(uptime_activity)
            db.session.add(downtime_activity)
            db.session.commit()

    return "Created fake data"


def change_job(current_job, time, machine_id):
    if current_job is not None:
        current_job.end_time = time

    new_job = Job(start_time=time,
                  job_number="X-" + str(randrange(1, 1000)),
                  machine_id=machine_id,
                  user_id=randrange(0,5))
    db.session.add(new_job)
    db.session.commit()
    return new_job
