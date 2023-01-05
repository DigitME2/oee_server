from datetime import datetime, timedelta
from random import randrange

from flask import current_app

from app.extensions import db
from app.default.models import ActivityCode, Machine, InputDevice, Activity, MachineGroup
from app.login.models import User
from config import Config


def setup_demo_database():
    """ Enter default values into the database on its first run"""
    db.create_all()

    # todo

    if len(MachineGroup.query.all()) == 0:
        if Config.DEMO_MODE:
            group1 = MachineGroup(name="Cutting")
            group2 = MachineGroup(name="Milling")
            current_app.logger.info("Created default machine groups on first startup")
            db.session.add(group1)
            db.session.add(group2)
            db.session.commit()

    create_demo_machines()
    if len(Settings.query.all()) == 0:
        if Config.DEMO_MODE:
            first_start = datetime.now() - timedelta(days=Config.DAYS_BACKFILL)

    if len(DemoSettings.query.all()) == 0:
        settings = DemoSettings(last_machine_simulation=(datetime.now() - timedelta(days=7)))
        db.session.add(settings)
        db.session.commit()
        current_app.logger.info("Created default settings on first startup")


def create_demo_activity_codes():
    ac1 = ActivityCode(short_description="Operator Break",
                       long_description="Operator has taken a break",
                       graph_colour="#dd9313")
    db.session.add(ac1)

    ac2 = ActivityCode(short_description="No material",
                       long_description="The machine is short of material",
                       graph_colour="#d60092")
    db.session.add(ac2)

    ac3 = ActivityCode(short_description="Scheduled Maintenance",
                       long_description="",
                       graph_colour="#00d6cf")
    db.session.add(ac3)
    db.session.commit()
    current_app.logger.info("Created demo activity codes on first startup")


def create_demo_machines():
    for machine_name in ["Brother 1",
                         "Brother 2",
                         "Bridgeport 1",
                         "Bridgeport 2",
                         "Makino",
                         "FANUC 1",
                         "FANUC 2",
                         "FANUC 3"]:
        current_app.logger.info(f"Creating demo machine and tablet {machine_name}")
        machine = Machine(name=machine_name,
                          workflow_type="default",
                          group_id=randrange(1, 3),
                          shift_id=1,
                          job_start_input_type="cycle_time_seconds")
        db.session.add(machine)
        db.session.flush()
        db.session.refresh(machine)
        # Create the first activity
        act_start = datetime.now() - timedelta(days=Config.DAYS_BACKFILL)
        first_act = Activity(start_time=act_start,
                             machine_id=machine.id,
                             machine_state=Config.MACHINE_STATE_UNPLANNED_DOWNTIME,
                             activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID)
        db.session.add(first_act)
        db.session.flush()
        db.session.refresh(first_act)
        machine.current_activity_id = first_act.id
        # Create an input device for each machine
        input_device = InputDevice(uuid=machine_name, name=machine_name, machine_id=machine.id)
        db.session.add(input_device)

    db.session.commit()


def create_demo_users():
    for name in names:
        user = User(username=name, admin=True)
        db.session.add(user)
        if name == "admin":
            user.set_password("digitme2")
        else:
            db.session.flush()
            db.session.refresh(user)
            user.set_password(str(user.id))
        db.session.commit()


def create_demo_groups():
    group1 = MachineGroup(name="Cutting")
    group2 = MachineGroup(name="Milling")
    current_app.logger.info("Created default machine groups on first startup")
    db.session.add(group1)
    db.session.add(group2)
    db.session.commit()

names = [
    "admin",
    "Pam",
    "Cyril",
    "Lana",
    "Barry",
    "Cheryl",
    "Ray",
    "Brett",
    "Sterling",
    "Mallory",
    "Leonard",
    "Ron",
    "Arthur",
    "Mitsuko",
    "Alan",
    "Conway",
    "Algernop",
    "Katya",
    "Slater"
]
