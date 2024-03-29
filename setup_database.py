from datetime import datetime, time

from flask import current_app

from app.default.helpers import DAYS, create_shift_day
from app.default.models import ActivityCode, Settings, Shift, MachineGroup, \
    SHIFT_STRFTIME_FORMAT, Machine, Activity
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
        if Config.TESTING:
            create_default_machine()


def create_default_settings():
    first_start = datetime.now()
    settings = Settings(first_start=first_start)
    db.session.add(settings)
    db.session.commit()
    current_app.logger.info("Created default settings on first startup")


def create_default_shift():
    shift = Shift(name="9-5")
    db.session.add(shift)
    db.session.flush()
    db.session.refresh(shift)
    for day in DAYS:
        shift_start = time(9, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
        shift_end = time(17, 0, 0, 0).strftime(SHIFT_STRFTIME_FORMAT)
        create_shift_day(day, shift_start=shift_start, shift_end=shift_end, shift_id=shift.id)
    db.session.commit()
    current_app.logger.info("Created default schedule on first startup")


def create_default_group():
    group = MachineGroup(name="Group 1")
    current_app.logger.info("Created default machine group on first startup")
    db.session.add(group)
    db.session.commit()


def create_default_activity_codes():
    unexplained_code = ActivityCode(id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                                    short_description='Down',
                                    long_description="Downtime that doesn't have an explanation from the user",
                                    machine_state=Config.MACHINE_STATE_UNPLANNED_DOWNTIME,
                                    graph_colour='#b22222',
                                    downtime_category=Config.DOWNTIME_CATEGORIES[0][0])
    db.session.add(unexplained_code)
    uptime_code = ActivityCode(id=Config.UPTIME_CODE_ID,
                               short_description='Up',
                               long_description='The machine is in use',
                               machine_state=Config.MACHINE_STATE_UPTIME,
                               graph_colour='#00ff80')
    db.session.add(uptime_code)
    planned_downtime_code = ActivityCode(id=Config.CLOSED_CODE_ID,
                                         short_description='Closed',
                                         long_description='Planned downtime outside of shift hours',
                                         machine_state=Config.MACHINE_STATE_PLANNED_DOWNTIME,
                                         graph_colour='#C6C6C6')
    db.session.add(planned_downtime_code)
    overtime_code = ActivityCode(id=Config.OVERTIME_CODE_ID,
                                 short_description='Overtime',
                                 long_description='Uptime outside of shift hours',
                                 machine_state=Config.OVERTIME_CODE_ID,
                                 graph_colour='#00ff80')
    db.session.add(overtime_code)
    db.session.commit()
    current_app.logger.info("Created default activity codes on first startup")

def create_default_machine():

    machine1 = Machine(name="Machine 1",
                       active=True,
                       group_id=1,
                       shift_id=1,
                       current_activity_id=0,
                       workflow_type="default",
                       job_start_input_type="cycle_time_seconds",
                       job_number_input_type="number",
                       end_job_on_shift_end=True,
                       autofill_job_start_amount=0)
    db.session.add(machine1)
    db.session.commit()
    current_app.logger.info("Created default machine on first startup")

    first_act = Activity(start_time=datetime.now(),
                         machine_id=1,
                         activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID)
    db.session.add(first_act)
    db.session.add(first_act)
    db.session.flush()
    db.session.refresh(first_act)
    machine1.current_activity_id = first_act.id
    current_app.logger.info("Created activity on first startup")
    db.session.commit()


if __name__ == "__main__":
    from app import create_app
    # Just initialising the app will call setup_database()
    app = create_app()
