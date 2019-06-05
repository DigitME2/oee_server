from app import db
from app.login.models import create_default_users
import logging

logger = logging.getLogger('flask.app')

UNEXPLAINED_DOWNTIME_CODE_ID = 0  # The ID of the activity code that represents unexplained downtime
UPTIME_CODE_ID = 1  # The ID of the activity code that for uptime. Preferably 0 to keep it on the bottom of the graph

MACHINE_STATE_OFF = 0
MACHINE_STATE_RUNNING = 1
MACHINE_STATE_ERROR = 2


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)

    activities = db.relationship('Activity')
    jobs = db.relationship('Job', backref='machine')

    def __repr__(self):
        return f"<Machine '{self.name}' (ID {self.id})"


class Job(db.Model):
    # Each user_id is only allowed one job with active=true Check constraint prevents false values for the active column
    __table_args__ = (db.UniqueConstraint('user_id', 'active'), db.CheckConstraint('active'))
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Float, nullable=False)
    end_time = db.Column(db.Float)
    job_number = db.Column(db.String, nullable=False)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    active = db.Column(db.Boolean)  # This should either be true or null

    activities = db.relationship('Activity', backref='job')

    def __repr__(self):
        return f"<Job {self.job_number} (ID {self.id})>"


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    machine_state = db.Column(db.Integer, nullable=False)
    explanation_required = db.Column(db.Boolean)
    timestamp_start = db.Column(db.Float, nullable=False)
    timestamp_end = db.Column(db.Float)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'))
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))

    def __repr__(self):
        return f"<Activity machine:{self.machine_id} machine_state:{self.machine_state} (ID {self.id})>"


class ActivityCode(db.Model):
    """ Holds the codes to identify activities"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    short_description = db.Column(db.String)
    long_description = db.Column(db.String)
    graph_colour = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)

    activities = db.relationship('Activity', backref='activity_code')

    def __repr__(self):
        return f"ActivityCode '{self.code}' (ID {self.id})>"


class Settings(db.Model):
    # Only allow one row in this table
    unique = db.Column(db.String, db.CheckConstraint('1'), primary_key=True, default="1")
    threshold = db.Column(db.Integer)


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
        logger.info("Created default activity codes on first startup")

    if len(Machine.query.all()) == 0:
        machine1 = Machine(name="Machine 1")
        db.session.add(machine1)
        db.session.commit()
        logger.info("Created default machine on first startup")

    if len(Settings.query.all()) == 0:
        settings = Settings(threshold=500)
        db.session.add(settings)
        db.session.commit()
        logger.info("Created default settings on first startup")
