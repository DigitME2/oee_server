from app import db
from app.default.models import ActivityCode, UNEXPLAINED_DOWNTIME_CODE_ID, UPTIME_CODE_ID, Machine, Settings
from app.login.models import create_default_users
from flask import current_app


def setup_database():

    """ Enter default values into the database on its first run"""
    db.create_all()

    create_default_users()

    if len(ActivityCode.query.all()) == 0:
        unexplainedcode = ActivityCode(id=UNEXPLAINED_DOWNTIME_CODE_ID,
                                       code="EX",
                                       short_description='Unexplained',
                                       long_description="Downtime that doesn't have an explanation from the user",
                                       graph_colour='rgb(178,34,34)')
        db.session.add(unexplainedcode)
        uptimecode = ActivityCode(id=UPTIME_CODE_ID,
                                  code="UP",
                                  short_description='Uptime',
                                  long_description='The machine is in use',
                                  graph_colour='rgb(0, 255, 128)')
        db.session.add(uptimecode)
        db.session.commit()
        current_app.logger.info("Created default activity codes on first startup")

    if len(Machine.query.all()) == 0:
        machine1 = Machine(name="Machine 1")
        db.session.add(machine1)
        db.session.commit()
        current_app.logger.info("Created default machine on first startup")

    if len(Settings.query.all()) == 0:
        settings = Settings(threshold=500)
        db.session.add(settings)
        db.session.commit()
        current_app.logger.info("Created default settings on first startup")
