from app import db
from time import time


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_number = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String, unique=True)

    activities = db.relationship('Activity')
    jobs = db.relationship('Job')


class Job(db.Model):
    # Each user_id is only allowed one job with active=true Check constraint prevents false values for the active column
    __table_args__ = (db.UniqueConstraint('user_id', 'active'), db.CheckConstraint('active'))
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Integer, nullable=False)
    end_time = db.Column(db.Integer)
    job_number = db.Column(db.String, nullable=False, unique=True)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    active = db.Column(db.Boolean)  # This should either be true or null

    activities = db.relationship('Activity')


class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    works_order_number = db.Column(db.String, nullable=False)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'), nullable=False)
    timestamp_start = db.Column(db.Integer, nullable=False)
    timestamp_end = db.Column(db.Integer)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))


class ActivityCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_code = db.Column(db.Integer, nullable=False, unique=True)
    description = db.Column(db.String)

    activities = db.relationship('Activity', backref='code')


