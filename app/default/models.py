import logging

import redis
from sqlalchemy import event

from app.extensions import db
from config import Config

logger = logging.getLogger('flask.app')

SHIFT_STRFTIME_FORMAT = "%H%M"  # Time is stored in the database as a string and converted to a time object

# Stores activity code exclusions. If a machine has an activity code in this table, its device won't show this code.
machine_activity_codes_association_table = db.Table('machine_activity_code_exclusion', db.Model.metadata,
                                                    db.Column('machine_id', db.ForeignKey('machine.id')),
                                                    db.Column('activity_code_id', db.ForeignKey('activity_code.id')))


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    active_job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    active_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    current_activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))
    job_start_activity_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'), default=Config.UPTIME_CODE_ID)
    autofill_job_start_input = db.Column(db.Boolean)
    autofill_job_start_amount = db.Column(db.Float)
    workflow_type = db.Column(db.String(100))
    job_start_input_type = db.Column(db.String(100))
    group_id = db.Column(db.Integer, db.ForeignKey('machine_group.id'))
    active = db.Column(db.Boolean, default=True)

    excluded_activity_codes = db.relationship('ActivityCode', secondary=machine_activity_codes_association_table)
    scheduled_activities = db.relationship('ScheduledActivity', backref='machine')
    activities = db.relationship('Activity', foreign_keys="[Activity.machine_id]", backref='machine')
    current_activity = db.relationship('Activity', foreign_keys=[current_activity_id])
    active_job = db.relationship('Job', foreign_keys=[active_job_id])
    active_user = db.relationship('User', foreign_keys=[active_user_id])
    input_device = db.relationship('InputDevice', uselist=False, back_populates="machine")

    def __repr__(self):
        return f"<Machine '{self.name}' (ID {self.id})"


class InputDevice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))
    active_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    active_user_session_id = db.Column(db.Integer, db.ForeignKey('user_session.id'))

    machine = db.relationship("Machine", uselist=False, back_populates="input_device")
    active_user_session = db.relationship(
        "UserSession", foreign_keys=[active_user_session_id], uselist=False)


class MachineGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    machines = db.relationship('Machine', backref='machine_group')


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    job_number = db.Column(db.String(100), nullable=False)
    part_number = db.Column(db.String(100))
    ideal_cycle_time_s = db.Column(db.Integer)
    quantity_produced = db.Column(db.Integer, default=0)
    quantity_rejects = db.Column(db.Integer, default=0)
    machine_id = db.Column(db.Integer)
    active = db.Column(db.Boolean)
    notes = db.Column(db.String(100))

    activities = db.relationship('Activity', backref='job')
    quantities = db.relationship('ProductionQuantity', backref='job')

    def __repr__(self):
        return f"<Job {self.job_number} (ID {self.id})>"


class ProductionQuantity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    time = db.Column(db.DateTime)
    quantity_produced = db.Column(db.Integer)
    quantity_rejects = db.Column(db.Integer)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'), nullable=False)
    machine_state = db.Column(db.Integer, nullable=False)
    time_start = db.Column(db.DateTime, nullable=False)
    time_end = db.Column(db.DateTime)
    explanation_required = db.Column(db.Boolean)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"<Activity machine:{self.machine_id} machine_state:{self.machine_state} (ID {self.id})>"


@event.listens_for(Activity, 'after_insert')
def receive_after_update(mapper, connection, target: Activity):
    """ Publish changes to redis to allow updates to be pushed to clients"""
    # Don't publish activities ending
    if target.time_end is None:
        r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT)
        r.publish("machine" + str(target.machine_id) + "activity", target.activity_code_id)


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    mon_start = db.Column(db.String(100))
    mon_end = db.Column(db.String(100))
    tue_start = db.Column(db.String(100))
    tue_end = db.Column(db.String(100))
    wed_start = db.Column(db.String(100))
    wed_end = db.Column(db.String(100))
    thu_start = db.Column(db.String(100))
    thu_end = db.Column(db.String(100))
    fri_start = db.Column(db.String(100))
    fri_end = db.Column(db.String(100))
    sat_start = db.Column(db.String(100))
    sat_end = db.Column(db.String(100))
    sun_start = db.Column(db.String(100))
    sun_end = db.Column(db.String(100))

    machines = db.relationship('Machine', backref='schedule')

    def get_shifts(self):
        """" Return a dictionary of tuples mapping the day of the week to the shift pattern"""
        return {0: (self.mon_start, self.mon_end),
                1: (self.tue_start, self.tue_end),
                2: (self.wed_start, self.wed_end),
                3: (self.thu_start, self.thu_end),
                4: (self.fri_start, self.fri_end),
                5: (self.sat_start, self.sat_end),
                6: (self.sun_start, self.sun_end)}


class ScheduledActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    scheduled_machine_state = db.Column(db.Integer, nullable=False)
    time_start = db.Column(db.DateTime, nullable=False)
    time_end = db.Column(db.DateTime)


class ActivityCode(db.Model):
    """ Holds the codes to identify activities"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(100))
    short_description = db.Column(db.String(100), nullable=False, unique=True)
    long_description = db.Column(db.String(100))
    graph_colour = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)

    activities = db.relationship('Activity', backref='activity_code')

    def __repr__(self):
        return f"<ActivityCode code:'{self.code}' (ID {self.id})>"


class Settings(db.Model):
    # Only allow one row in this table
    id = db.Column(db.Integer, db.CheckConstraint("id = 1"), primary_key=True)
    first_start = db.Column(db.DateTime)
    dashboard_update_interval_s = db.Column(db.Integer)
    job_number_input_type = db.Column(db.String(100))
    allow_delayed_job_start = db.Column(db.Boolean, default=False)
    allow_concurrent_user_jobs = db.Column(db.Boolean, default=True)


