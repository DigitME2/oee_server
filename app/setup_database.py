from datetime import datetime, time

from flask import current_app

from app.default.helpers import DAYS
from app.default.models import ActivityCode, Settings, Shift, MachineGroup, \
    SHIFT_STRFTIME_FORMAT, ShiftPeriod
from app.extensions import db
from app.login.models import create_default_users
from config import Config


def setup_database():
    """ Enter default values into the database on its first run"""
    db.create_all()
    if len(Settings.query.all()) == 0:
        create_default_users()
        create_default_settings()
        create_default_activity_codes()
        create_default_group()
        create_default_shift()


def create_default_settings():
    first_start = datetime.now()
    settings = Settings(job_number_input_type="number", allow_delayed_job_start=False,
                        dashboard_update_interval_s=10, first_start=first_start)
    db.session.add(settings)
    db.session.commit()
    current_app.logger.info("Created default settings on first startup")


def create_default_shift():
    shift = Shift(name="Default")
    db.session.add(shift)
    db.session.flush()
    db.session.refresh(shift)
    for day in DAYS:
        midnight = time(0, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
        shift_start = time(9, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
        shift_end = time(18, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
        period_1 = ShiftPeriod(shift_id=shift.id, shift_state=Config.MACHINE_STATE_PLANNED_DOWNTIME,
                               day=day, start_time=midnight)
        db.session.add(period_1)
        period_2 = ShiftPeriod(shift_id=shift.id, shift_state=Config.MACHINE_STATE_UPTIME,
                               day=day, start_time=shift_start)
        db.session.add(period_2)
        period_3 = ShiftPeriod(shift_id=shift.id, shift_state=Config.MACHINE_STATE_PLANNED_DOWNTIME,
                               day=day, start_time=shift_end)
        db.session.add(period_3)
    db.session.commit()
    current_app.logger.info("Created default schedule on first startup")


def create_default_group():
    group = MachineGroup(name="Group 1")
    current_app.logger.info("Created default machine group on first startup")
    db.session.add(group)
    db.session.commit()


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
