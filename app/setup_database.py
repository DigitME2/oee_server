import os
from app import db
from app.default.models import ActivityCode, Machine, Settings
from config import Config
from app.login.models import create_default_users
from flask import current_app


def setup_database():

    """ Enter default values into the database on its first run"""
    db.create_all()

    create_default_users()

    if len(ActivityCode.query.all()) == 0:
        unexplainedcode = ActivityCode(id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                                       code="EX",
                                       short_description='Unexplained',
                                       long_description="Downtime that doesn't have an explanation from the user",
                                       graph_colour='#b22222')
        db.session.add(unexplainedcode)
        uptimecode = ActivityCode(id=Config.UPTIME_CODE_ID,
                                  code="UP",
                                  short_description='Uptime',
                                  long_description='The machine is in use',
                                  graph_colour='#00ff80')
        db.session.add(uptimecode)
        db.session.commit()
        current_app.logger.info("Created default activity codes on first startup")

    if len(Machine.query.all()) == 0:
        machine1 = Machine(name="Machine 1",
                           device_ip="127.0.0.1",
                           schedule_start_1=8,
                           schedule_end_1=12,
                           schedule_start_2=13,
                           schedule_end_2=17,
                           schedule_start_3=17,
                           schedule_end_3=20)
        db.session.add(machine1)
        db.session.commit()
        current_app.logger.info("Created default machine on first startup")

    if len(Settings.query.all()) == 0:
        settings = Settings(threshold=500)
        db.session.add(settings)
        db.session.commit()
        current_app.logger.info("Created default settings on first startup")
        current_app.logger.warn("Ending process to complete first time setup...")
        os.abort()
