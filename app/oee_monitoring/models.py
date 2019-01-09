from app import db

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    jobs = db.relationship('Job')

    #TODO Dummy code
    is_active = True


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Integer)
    end_time = db.Column(db.Integer)
    job_number = db.Column(db.String)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    activities = db.relationship('Activity')


class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    works_order_number = db.Column(db.String)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'))
    timestamp_start = db.Column(db.Integer)
    timestamp_end = db.Column(db.Integer)


class ActivityCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_code = db.Column(db.Integer)
    description = db.Column(db.String)

    activities = db.relationship('Activity', backref='code')


