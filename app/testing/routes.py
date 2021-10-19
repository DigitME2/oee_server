from random import randrange

from app.data_analysis.oee import *
from app.default.db_helpers import machine_schedule_active
from app.default.machine_simulator import backfill_missed_simulations
from app.default.models import *
from app.testing import bp
from config import Config
from flask import render_template, current_app


@bp.route('/test')
def test():
    backfill_missed_simulations()
    return "test"


def sort_activities(act):
    return act.activity_code.id


@bp.route('/createdata')
def create_data():
    """ Creates fake data to use for testing purposes"""

    start = datetime(year=2020, month=6, day=21, hour=0, minute=0).timestamp()
    finish = datetime(year=2020, month=6, day=22, hour=0, minute=0).timestamp()

    create_activities(machine_id=4, user_id=8, timestamp_start=start, timestamp_end=finish)
    return "created"


def create_activities(machine_id, user_id, timestamp_start, timestamp_end):
    all_activity_codes = ActivityCode.query.all()
    time = timestamp_start
    current_job = None
    while time <= timestamp_end:
        # chance of changing active job
        if randrange(0, 3) > 1:
            current_job = change_job(current_job, time, user_id, machine_id)
        if current_job is None:
            job_id = None
        else:
            job_id = current_job.id
        uptime_activity = Activity(machine_id=machine_id,
                                   timestamp_start=time,
                                   machine_state=1,
                                   activity_code_id=Config.UPTIME_CODE_ID,
                                   job_id=job_id,
                                   user_id=user_id)
        time += randrange(400, 10000)
        uptime_activity.timestamp_end = time

        machine_state = randrange(0, 3)
        if machine_state == 1:
            machine_state = 0
        downtime_activity = Activity(machine_id=machine_id,
                                     timestamp_start=time,
                                     machine_state=machine_state,
                                     activity_code_id=randrange(2, 5),
                                     job_id=job_id,
                                     user_id=user_id)
        time += randrange(60, 2000)
        downtime_activity.timestamp_end = time
        db.session.add(uptime_activity)
        db.session.add(downtime_activity)
        db.session.commit()


def change_job(current_job, time, user_id, machine_id):
    if current_job is not None:
        current_job.end_time = time
        current_job.active = None

    new_job = Job(start_time=time,
                  user_id=user_id,
                  user_session_id=1,
                  wo_number="WO-" + str(randrange(1, 1000)),
                  part_number="P" + str(randrange(1, 1000)),
                  planned_set_time=str(randrange(1, 100)),
                  planned_run_time=str(randrange(1, 100)),
                  planned_quantity=str(randrange(1, 100)),
                  planned_cycle_time=str(randrange(1, 100)),
                  actual_quantity=str(randrange(1, 100)),
                  machine_id=machine_id,
                  production_scrap=str(randrange(1,100)),
                  active=True)

    db.session.add(new_job)
    db.session.commit()
    return new_job
