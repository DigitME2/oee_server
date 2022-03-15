import logging

from app.extensions import db
from config import Config

logger = logging.getLogger('flask.app')

SHIFT_STRFTIME_FORMAT = "%H%M"  # Time is stored in the database as a string and converted to a time object


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    workflow_type = db.Column(db.String)
    job_start_input_type = db.Column(db.String)
    group_id = db.Column(db.Integer, db.ForeignKey('machine_group.id'))
    device_ip = db.Column(db.String, unique=True)
    active = db.Column(db.Boolean, default=True)
    user_sessions = db.relationship("UserSession", backref="machine")
    activities = db.relationship('Activity', backref='machine')
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'))

    scheduled_activities = db.relationship('ScheduledActivity', backref='machine')
    jobs = db.relationship('Job', backref='machine')

    def __repr__(self):
        return f"<Machine '{self.name}' (ID {self.id})"


class MachineGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)

    machines = db.relationship('Machine', backref='machine_group')


class Job(db.Model):
    # Each user_id is only allowed one job with active=true Check constraint prevents false values for the active column
    __table_args__ = (db.UniqueConstraint('user_id', 'active'), db.CheckConstraint('active'))
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    wo_number = db.Column(db.String, nullable=False)
    part_number = db.Column(db.String)
    ideal_cycle_time_s = db.Column(db.Integer)
    quantity_produced = db.Column(db.Integer)
    quantity_rejects = db.Column(db.Integer)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_session_id = db.Column(db.Integer, db.ForeignKey('user_session.id'), nullable=False)
    active = db.Column(db.Boolean)  # This should either be true or null
    notes = db.Column(db.String)

    activities = db.relationship('Activity', backref='job')

    def __repr__(self):
        return f"<Job {self.wo_number} (ID {self.id})>"


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


class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)

    mon_start = db.Column(db.String)
    mon_end = db.Column(db.String)
    tue_start = db.Column(db.String)
    tue_end = db.Column(db.String)
    wed_start = db.Column(db.String)
    wed_end = db.Column(db.String)
    thu_start = db.Column(db.String)
    thu_end = db.Column(db.String)
    fri_start = db.Column(db.String)
    fri_end = db.Column(db.String)
    sat_start = db.Column(db.String)
    sat_end = db.Column(db.String)
    sun_start = db.Column(db.String)
    sun_end = db.Column(db.String)

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
    code = db.Column(db.String, unique=True)
    short_description = db.Column(db.String)
    long_description = db.Column(db.String)
    graph_colour = db.Column(db.String)
    active = db.Column(db.Boolean, default=True)

    activities = db.relationship('Activity', backref='activity_code')

    def __repr__(self):
        return f"<ActivityCode code:'{self.code}' (ID {self.id})>"


class Settings(db.Model):
    # Only allow one row in this table
    id = db.Column(db.Integer, db.CheckConstraint("id = 1"), primary_key=True)
    dashboard_update_interval_s = db.Column(db.Integer)
    job_number_input_type = db.Column(db.String)
    allow_delayed_job_start = db.Column(db.Boolean)
    first_start = db.Column(db.DateTime)


class DemoSettings(db.Model):
    # Only allow one row in this table
    id = db.Column(db.Integer, db.CheckConstraint("id = 1"), primary_key=True)
    last_machine_simulation = db.Column(db.DateTime)


