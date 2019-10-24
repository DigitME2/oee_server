import os
from datetime import datetime, time

from flask import current_app

from app import db
from app.default.models import Activity, ActivityCode, Machine, Settings, Schedule, SHIFT_STRFTIME_FORMAT
from app.login.models import create_default_users
from config import Config


def setup_database():

    """ Enter default values into the database on its first run"""
    db.create_all()

    create_default_users()

    if len(ActivityCode.query.all()) == 0:

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
        setting_code = ActivityCode(id=Config.SETTING_CODE_ID,
                                    code="ST",
                                    short_description="Setting",
                                    long_description="The machine is being set up",
                                    graph_colour="#ff8000")
        db.session.add(setting_code)
        db.session.commit()
        current_app.logger.info("Created default activity codes on first startup")

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

    if len(Machine.query.all()) == 0:
        machine1 = Machine(name="Machine 1",
                           device_ip="127.0.0.1",
                           group="1",
                           schedule_id=1)
        db.session.add(machine1)
        db.session.commit()
        current_app.logger.info("Created default machine on first startup")

        act = Activity(machine_id=machine1.id,
                       timestamp_start=datetime.now().timestamp(),
                       machine_state=Config.MACHINE_STATE_OFF,
                       activity_code_id=Config.NO_USER_CODE_ID)
        db.session.add(act)
        db.session.commit()
        current_app.logger.info("Created activity on first startup")


        db.session.commit()

    if len(Settings.query.all()) == 0:
        settings = Settings(threshold=500, dashboard_update_interval_s=10)
        db.session.add(settings)
        db.session.commit()
        current_app.logger.info("Created default settings on first startup")

