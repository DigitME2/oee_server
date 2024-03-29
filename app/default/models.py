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
    schedule_state = db.Column(db.Integer)
    shift_id = db.Column(db.Integer, db.ForeignKey('shift.id'))
    end_job_on_shift_end = db.Column(db.Boolean, default=True)
    job_start_activity_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'), default=Config.UPTIME_CODE_ID)
    autofill_job_start_input = db.Column(db.Boolean)
    autofill_job_start_amount = db.Column(db.Float)
    workflow_type = db.Column(db.String(100))
    job_start_input_type = db.Column(db.String(100))
    group_id = db.Column(db.Integer, db.ForeignKey('machine_group.id'))
    job_number_input_type = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)

    excluded_activity_codes = db.relationship('ActivityCode', secondary=machine_activity_codes_association_table)
    activities = db.relationship('Activity', foreign_keys="[Activity.machine_id]", back_populates='machine')
    current_activity = db.relationship('Activity', foreign_keys=[current_activity_id])
    active_job = db.relationship('Job', foreign_keys=[active_job_id])
    active_user = db.relationship('User', foreign_keys=[active_user_id])
    input_device = db.relationship('InputDevice', uselist=False, back_populates="machine")
    machine_group = db.relationship('MachineGroup', uselist=False)
    shift = db.relationship('Shift')

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
    active_user = db.relationship("User", uselist=False)
    active_user_session = db.relationship(
        "UserSession", foreign_keys=[active_user_session_id], uselist=False)


class MachineGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    machines = db.relationship('Machine', back_populates='machine_group')


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    job_number = db.Column(db.String(100), nullable=False)
    part_number = db.Column(db.String(100))
    ideal_cycle_time_s = db.Column(db.Integer)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'))
    active = db.Column(db.Boolean)
    notes = db.Column(db.String(100))

    quantities = db.relationship('ProductionQuantity', back_populates='job')
    machine = db.relationship('Machine', uselist=False, foreign_keys=[machine_id])

    def __repr__(self):
        return f"<Job {self.job_number} (ID {self.id})>"

    def get_total_good_quantity(self):
        total_good_qty = 0
        for q in self.quantities:
            if q.quantity_good:
                total_good_qty += q.quantity_good
        return total_good_qty

    def get_total_reject_quantity(self):
        total_reject_qty = 0
        for q in self.quantities:
            if q.quantity_rejects:
                total_reject_qty += q.quantity_rejects
        return total_reject_qty

    def get_total_quantity(self):
        return self.get_total_good_quantity() + self.get_total_reject_quantity()


class ProductionQuantity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    quantity_good = db.Column(db.Integer)
    quantity_rejects = db.Column(db.Integer)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)

    job = db.relationship("Job", uselist=False)


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    explanation_required = db.Column(db.Boolean)
    notes = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    machine = db.relationship("Machine", foreign_keys="[Activity.machine_id]", uselist=False)
    user = db.relationship("User", uselist=False)
    activity_code = db.relationship("ActivityCode", uselist=False)

    def __repr__(self):
        return f"<Activity machine:{self.machine_id} (ID {self.id})>"


@event.listens_for(Activity, 'after_insert')
def receive_after_update(mapper, connection, target: Activity):
    """ Publish changes to redis to allow updates to be pushed to clients"""
    # Don't publish activities ending
    if target.end_time is None:
        r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT)
        r.publish("machine" + str(target.machine_id) + "activity", target.activity_code_id)


class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    machines = db.relationship('Machine', back_populates='shift')
    shift_periods = db.relationship('ShiftPeriod', back_populates='shift')


class ShiftPeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shift_id = db.Column(db.Integer, db.ForeignKey("shift.id"))
    shift_state = db.Column(db.Integer)
    day = db.Column(db.String(5))
    start_time = db.Column(db.String(20))

    shift = db.relationship('Shift')


class ActivityCode(db.Model):
    """ Holds the codes to identify activities"""
    id = db.Column(db.Integer, primary_key=True)
    short_description = db.Column(db.String(100), nullable=False, unique=True)
    long_description = db.Column(db.String(100))
    machine_state = db.Column(db.Integer, nullable=False)
    downtime_category = db.Column(db.String(100))
    graph_colour = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)

    activities = db.relationship('Activity', back_populates='activity_code')

    def __repr__(self):
        return f"<ActivityCode code:'{self.code}' (ID {self.id})>"


class Settings(db.Model):
    # Only allow one row in this table
    id = db.Column(db.Integer, db.CheckConstraint("id = 1"), primary_key=True)
    first_start = db.Column(db.DateTime)
