from app import db
from time import time


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True)

    activities = db.relationship('Activity')
    jobs = db.relationship('Job')

    def is_in_use(self):
        """Returns true if there is an active activity for this machine"""
        for j in self.jobs:
            Activity.query.filter_by(active=True, job_id=j.id)

    #TODO Dummy code
    is_active = True


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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'), nullable=False)
    active = db.Column(db.Boolean, default=True)
    timestamp_start = db.Column(db.Integer, nullable=False)
    timestamp_end = db.Column(db.Integer)

    def end_activity(self):
        self.timestamp_end = time()
        self.active = False


class ActivityCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activity_code = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String)

    activities = db.relationship('Activity', backref='code')


