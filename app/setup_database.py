from datetime import datetime, time, timedelta
from random import randrange

from flask import current_app

from app.default.db_helpers import DAYS
from app.default.models import Activity, ActivityCode, Machine, Settings, Shift, MachineGroup, \
    SHIFT_STRFTIME_FORMAT, ShiftPeriod
from app.demo.models import DemoSettings
from app.extensions import db
from app.login.models import create_default_users
from config import Config


def setup_database():
    """ Enter default values into the database on its first run"""
    db.create_all()

    create_default_users()

    if len(ActivityCode.query.all()) == 0:
        create_default_activity_codes()
        if Config.DEMO_MODE:
            create_demo_activity_codes()

    if len(Shift.query.all()) == 0:
        shift = Shift(name="Default")
        db.session.add(shift)
        db.session.flush()
        db.session.refresh(shift)
        for day in DAYS:
            midnight = time(0, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
            shift_start = time(9, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
            shift_end = time(18, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
            period_1 = ShiftPeriod(shift_id=shift.id, day=day, start=midnight, end=shift_start)
            db.session.add(period_1)
            period_2 = ShiftPeriod(shift_id=shift.id, day=day, start=shift_start, end=shift_end)
            db.session.add(period_2)
            period_3 = ShiftPeriod(shift_id=shift.id, day=day, start=shift_end, end=midnight)
            db.session.add(period_3)
        db.session.commit()
        current_app.logger.info("Created default schedule on first startup")

    if len(MachineGroup.query.all()) == 0:
        if Config.DEMO_MODE:
            group1 = MachineGroup(name="Cutting")
            group2 = MachineGroup(name="Milling")
            current_app.logger.info("Created default machine groups on first startup")
            db.session.add(group1)
            db.session.add(group2)
            db.session.commit()
        else:
            group1 = MachineGroup(name="Group 1")
            current_app.logger.info("Created default machine group on first startup")
            db.session.add(group1)
            db.session.commit()

    if len(Machine.query.all()) == 0:
        if Config.DEMO_MODE:
            create_demo_machines()
        else:
            create_default_machine()

    if len(Settings.query.all()) == 0:
        if Config.DEMO_MODE:
            first_start = datetime.now() - timedelta(days=Config.DAYS_BACKFILL)
        else:
            first_start = datetime.now()
        settings = Settings(job_number_input_type="number", allow_delayed_job_start=False,
                            dashboard_update_interval_s=10, first_start=first_start)
        db.session.add(settings)
        db.session.commit()
        current_app.logger.info("Created default settings on first startup")

    if Config.DEMO_MODE:
        if len(DemoSettings.query.all()) == 0:
            settings = DemoSettings(last_machine_simulation=(datetime.now() - timedelta(days=7)))
            db.session.add(settings)
            db.session.commit()
            current_app.logger.info("Created default settings on first startup")


def create_default_activity_codes():
    unexplained_code = ActivityCode(id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                                    code="DO",
                                    short_description='Down',
                                    long_description="Downtime that doesn't have an explanation from the user",
                                    graph_colour='#b22222')
    db.session.add(unexplained_code)
    uptime_code = ActivityCode(id=Config.UPTIME_CODE_ID,
                               code="UP",
                               short_description='Up',
                               long_description='The machine is in use',
                               graph_colour='#00ff80')
    db.session.add(uptime_code)
    db.session.commit()
    current_app.logger.info("Created default activity codes on first startup")


def create_demo_activity_codes():
    ac1 = ActivityCode(code="OB",
                       short_description="Operator Break",
                       long_description="Operator has taken a break",
                       graph_colour="#dd9313")
    db.session.add(ac1)

    ac2 = ActivityCode(code="NM",
                       short_description="No material",
                       long_description="The machine is short of material",
                       graph_colour="#d60092")
    db.session.add(ac2)

    ac3 = ActivityCode(code="SM",
                       short_description="Scheduled Maintenance",
                       long_description="",
                       graph_colour="#00d6cf")
    db.session.add(ac3)
    db.session.commit()
    current_app.logger.info("Created demo activity codes on first startup")


def create_default_machine():
    machine1 = Machine(name="Machine 1",
                       group_id=1,
                       shift_id=1,
                       current_activity_id=0,
                       workflow_type="default",
                       job_start_input_type="cycle_time_seconds",
                       autofill_job_start_amount=0)
    db.session.add(machine1)
    db.session.flush()
    db.session.refresh(machine1)
    current_app.logger.info("Created default machine on first startup")

    act = Activity(machine_id=machine1.id,
                   time_start=datetime.now(),
                   machine_state=Config.MACHINE_STATE_OFF,
                   activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID)
    db.session.add(act)
    db.session.flush()
    db.session.refresh(act)
    machine1.current_activity_id = act.id
    db.session.commit()
    current_app.logger.info("Created activity on first startup")
    db.session.commit()


def create_demo_machines():
    ip_end = 0
    for machine_name in ["Brother 1",
                         "Brother 2",
                         "Bridgeport 1",
                         "Bridgeport 2",
                         "Makino",
                         "FANUC 1",
                         "FANUC 2",
                         "FANUC 3"]:
        ip_end += 1
        machine = Machine(name=machine_name,
                          workflow_type="default",
                          group_id=randrange(1, 3),
                          shift_id=1,
                          job_start_input_type="cycle_time_seconds")
        db.session.add(machine)
    db.session.commit()
    current_app.logger.info("Created default machine on first startup")
