from datetime import datetime, time, timedelta

from flask import current_app

from app.default.models import ActivityCode, Machine, Settings, Schedule, MachineGroup, SHIFT_STRFTIME_FORMAT
from app.demo.models import DemoSettings
from app.demo.db_setup import create_demo_activity_codes, create_demo_machines, create_demo_users, create_demo_groups
from app.extensions import db
from app.login.models import create_default_users, User
from config import Config


def setup_database():
    """ Enter default values into the database on its first run"""
    db.create_all()

    if len(User.query.all()) == 0:
        if Config.DEMO_MODE:
            create_demo_users()
        else:
            create_default_users()

    if len(ActivityCode.query.all()) == 0:
        create_default_activity_codes()
        if Config.DEMO_MODE:
            create_demo_activity_codes()

    if len(Schedule.query.all()) == 0:
        schedule1 = Schedule(name="Default",
                             mon_start=time(hour=6).strftime(SHIFT_STRFTIME_FORMAT),
                             mon_end=time(hour=22).strftime(SHIFT_STRFTIME_FORMAT),
                             tue_start=time(hour=6).strftime(SHIFT_STRFTIME_FORMAT),
                             tue_end=time(hour=22).strftime(SHIFT_STRFTIME_FORMAT),
                             wed_start=time(hour=6).strftime(SHIFT_STRFTIME_FORMAT),
                             wed_end=time(hour=22).strftime(SHIFT_STRFTIME_FORMAT),
                             thu_start=time(hour=6).strftime(SHIFT_STRFTIME_FORMAT),
                             thu_end=time(hour=22).strftime(SHIFT_STRFTIME_FORMAT),
                             fri_start=time(hour=6).strftime(SHIFT_STRFTIME_FORMAT),
                             fri_end=time(hour=22).strftime(SHIFT_STRFTIME_FORMAT),
                             sat_start=time(hour=6).strftime(SHIFT_STRFTIME_FORMAT),
                             sat_end=time(hour=22).strftime(SHIFT_STRFTIME_FORMAT),
                             sun_start=time(hour=6).strftime(SHIFT_STRFTIME_FORMAT),
                             sun_end=time(hour=22).strftime(SHIFT_STRFTIME_FORMAT))
        db.session.add(schedule1)
        db.session.commit()
        current_app.logger.info("Created default schedule on first startup")

    if len(MachineGroup.query.all()) == 0:
        if Config.DEMO_MODE:
            create_demo_groups()
        else:
            group1 = MachineGroup(name="Group 1")
            current_app.logger.info("Created default machine group on first startup")
            db.session.add(group1)
            db.session.commit()

    if len(Machine.query.all()) == 0 and Config.DEMO_MODE:
        create_demo_machines()

    if len(Settings.query.all()) == 0:
        if Config.DEMO_MODE:
            first_start = datetime.now() - timedelta(days=Config.DAYS_BACKFILL)
        else:
            first_start = datetime.now()
        settings = Settings(job_number_input_type="number", allow_delayed_job_start=False,
                            dashboard_update_interval_s=10, first_start=first_start, allow_concurrent_user_jobs=True)
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
    no_user_code = ActivityCode(id=Config.NO_USER_CODE_ID,
                                code="NU",
                                short_description="No User",
                                long_description="No user is logged onto the machine",
                                graph_colour="#ffffff")
    db.session.add(no_user_code)

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
