from app import db
from time import time

UNEXPLAINED_DOWNTIME_CODE = 0
UPTIME_CODE = 1


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_number = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String, unique=True)

    activities = db.relationship('Activity')
    jobs = db.relationship('Job', backref='machine')


class Job(db.Model):
    # Each user_id is only allowed one job with active=true Check constraint prevents false values for the active column
    __table_args__ = (db.UniqueConstraint('user_id', 'active'), db.CheckConstraint('active'))
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Integer, nullable=False)
    end_time = db.Column(db.Integer)
    job_number = db.Column(db.String, nullable=False)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    active = db.Column(db.Boolean)  # This should either be true or null

    activities = db.relationship('Activity')


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    machine_state = db.Column(db.String, nullable=False)
    activity_code = db.Column(db.Integer, db.ForeignKey('activity_code.code'))
    timestamp_start = db.Column(db.Integer, nullable=False)
    timestamp_end = db.Column(db.Integer)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))


class ActivityCode(db.Model):
    """ Holds the codes to identify activities"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)  # By default, code 1 is uptime
    short_description = db.Column(db.String)
    long_description = db.Column(db.String)

    activities = db.relationship('Activity', backref='code')


