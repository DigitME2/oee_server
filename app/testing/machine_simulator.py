import json
import random
from datetime import datetime
from random import randrange
from time import time, sleep
from app import db
from app import Config
from app.default.db_helpers import complete_last_activity

from app.login.models import User, UserSession

from app.default.models import Machine, Job, Activity


def create_new_demo_user(username, machine):
    user = User(username=username)
    user.set_password("secret_bot_password!!!")
    db.session.add(user)
    db.session.commit()
    user_session = UserSession(user_id=user.id,
                               machine_id=machine.id,
                               device_ip="",
                               timestamp_login=datetime.now().timestamp(),
                               active=True)
    db.session.add(user_session)
    db.session.commit()
    return user


def end_job(job):
    print(f"ending job")
    job.end_time = datetime.now().timestamp()
    job.active = None
    db.session.commit()


def start_new_job(machine, user):
    print(f"starting new job")
    session = UserSession.query.filter_by(user_id=user.id, active=True).first()
    job = Job(start_time=datetime.now().timestamp(),
              user_id=user.id,
              wo_number=random.randint(1, 100000),
              planned_run_time=random.randint(1, 1000),
              planned_quantity=random.randint(1, 100),
              machine_id=machine.id,
              active=True,
              user_session_id=session.id)
    db.session.add(job)
    db.session.commit()


def change_activity(machine, job, user):
    print(f"changing activity")
    complete_last_activity(machine_id=machine.id)
    # 80% chance the activity is uptime
    if random.random() < 0.8:
        new_activity = Activity(machine_id=machine.id,
                                timestamp_start=datetime.now().timestamp(),
                                machine_state=1,
                                activity_code_id=Config.UPTIME_CODE_ID,
                                job_id=job.id,
                                user_id=user.id)
    else:
        # otherwise the activity is downtime
        new_activity = Activity(machine_id=machine.id,
                                timestamp_start=datetime.now().timestamp(),
                                machine_state=0,
                                activity_code_id=randrange(2, 5),
                                job_id=job.id,
                                user_id=user.id)
    db.session.add(new_activity)
    db.session.commit()


def simulate_machines():
    for machine in Machine.query.all():
        print(f"simulating machine action for machine {machine.id}")
        # 66% chance to skip doing anything
        if random.random() < 0:
            print(f"not doing anything for machine {machine.id}")
            continue

        # Each machine has its own fake user. Create it if it does not exist
        username = machine.name + " user"
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = create_new_demo_user(username, machine)
            start_new_job(machine, user)

        if user.has_job():
            current_job = Job.query.filter_by(user_id=user.id, active=True).first()
            # 3% chance of ending job
            if random.random() < 0.03:
                end_job(current_job)
            # 20% chance to change activity
            if random.random() < 0.20:
                change_activity(machine, current_job, user)


        else:
            # 30% chance of starting a new job
            if random.random() < 0.3:
                start_new_job(machine, user)
