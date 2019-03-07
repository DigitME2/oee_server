from app import db
from time import time

UNEXPLAINED_DOWNTIME_CODE = 0
UPTIME_CODE = 1
ERROR_1_CODE = 2


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_number = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String, unique=True)

    activities = db.relationship('Activity')
    jobs = db.relationship('Job', backref='machine')


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Integer, nullable=False)
    end_time = db.Column(db.Integer)
    job_number = db.Column(db.String, nullable=False)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    works_order_number = db.Column(db.String, nullable=False)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    machine_state = db.Column(db.String, nullable=False)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'))
    timestamp_start = db.Column(db.Integer, nullable=False)
    timestamp_end = db.Column(db.Integer)



class ActivityCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_code = db.Column(db.Integer, nullable=False, unique=True)
    description = db.Column(db.String)

    activities = db.relationship('Activity', backref='code')


