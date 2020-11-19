import random
from datetime import datetime
from random import randrange

from flask import current_app

from app import Config
from app.default.db_helpers import complete_last_activity, machine_schedule_active
from app.default.models import Machine, Job, Activity
from app.extensions import db
from app.login.models import User, UserSession


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


def end_job(job, machine):
    current_app.logger.debug(f"ending job")
    job.end_time = datetime.now().timestamp()
    job.active = None
    complete_last_activity(machine_id=machine.id)
    db.session.commit()


def start_new_job(machine, user):
    current_app.logger.debug(f"Starting new job")
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
    current_app.logger.debug(f"changing activity")
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
    if not Config.DEMO_MODE:
        current_app.logger.warning("Fake data being created when app is not in DEMO_MODE")
    for machine in Machine.query.all():
        chance_to_skip_simulation = 0.90
        if random.random() < chance_to_skip_simulation:
            current_app.logger.debug(f"skipping machine {machine.id} simulation")
            continue
        current_app.logger.debug(f"simulating machine action for machine {machine.id}")
        # Get the machine's user by using the machine id as the index on a fake names list. Create it if it does not exist
        username = names[machine.id]
        user = User.query.filter_by(username=username).first()
        if user is None:
            user = create_new_demo_user(username, machine)
            start_new_job(machine, user)
        if not machine_schedule_active(machine):
            # Don't run jobs if the machine is not scheduled to be running
            if user.has_job():
                current_job = Job.query.filter_by(user_id=user.id, active=True).first()
                end_job(current_job, machine)
            else:
                continue
        if user.has_job():
            current_job = Job.query.filter_by(user_id=user.id, active=True).first()
            chance_to_end_job = 0.03
            if random.random() < chance_to_end_job:
                end_job(current_job, machine)
            chance_to_change_activity = 0.2
            if random.random() < chance_to_change_activity:
                change_activity(machine, current_job, user)


        else:
            chance_to_start_job = 0.3
            if random.random() < chance_to_start_job:
                start_new_job(machine, user)


names = [
    "Cameron",
    "Margot",
    "Jack",
    "Natashia",
    "Melva",
    "Kassie",
    "Hallie",
    "Shannon",
    "James",
    "Benito",
    "Ahmed",
    "Jaimee",
    "Nanci",
    "Markus",
    "Vina",
    "Nicolasa",
    "Shawnna",
    "Elton",
    "Gladis",
    "Donnette",
]