import os
from datetime import datetime

from flask import current_app

from app import db
from app.default.models import Activity, ActivityCode, Machine, Settings
from app.login.models import create_default_users
from config import Config


def setup_database():

    """ Enter default values into the database on its first run"""
    db.create_all()

    create_default_users()

    if len(ActivityCode.query.all()) == 0:
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

    if len(Machine.query.all()) == 0:
        machine1 = Machine(name="Machine 1",
                           device_ip="127.0.0.1",
                           group="1",
                           schedule_start_1="0800",
                           schedule_end_1="1200",
                           schedule_start_2="1300",
                           schedule_end_2="1700",
                           schedule_start_3="1700",
                           schedule_end_3="2000")
        db.session.add(machine1)
        db.session.commit()
        current_app.logger.info("Created default machine on first startup")

        act = Activity(machine_id=machine1.id,
                       timestamp_start=datetime.now().timestamp(),
                       machine_state=Config.MACHINE_STATE_OFF,
                       activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID)
        db.session.add(act)
        db.session.commit()
        current_app.logger.info("Created activity on first startup")

    if len(Settings.query.all()) == 0:
        settings = Settings(threshold=500)
        db.session.add(settings)
        db.session.commit()
        current_app.logger.info("Created default settings on first startup")
        current_app.logger.warn("Ending process to complete first time setup...")
        os.abort()
