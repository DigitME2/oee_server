import logging

from app import db

logger = logging.getLogger('flask.app')

SHIFT_STRFTIME_FORMAT = "%H%M"  # Time is stored in the database as a string and converted to a time object


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    group = db.Column(db.String)
    device_ip = db.Column(db.String, unique=True)
    active = db.Column(db.Boolean, default=True)
    schedule_start_1 = db.Column(db.String)
    schedule_end_1 = db.Column(db.String)
    schedule_start_2 = db.Column(db.String)
    schedule_end_2 = db.Column(db.String)
    schedule_start_3 = db.Column(db.String)
    schedule_end_3 = db.Column(db.String)

    user_sessions = db.relationship("UserSession", backref="machine")
    activities = db.relationship('Activity', backref='machine')
    jobs = db.relationship('Job', backref='machine')

    def __repr__(self):
        return f"<Machine '{self.name}' (ID {self.id})"


class Job(db.Model):
    # Each user_id is only allowed one job with active=true Check constraint prevents false values for the active column
    __table_args__ = (db.UniqueConstraint('user_id', 'active'), db.CheckConstraint('active'))
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Float, nullable=False)
    end_time = db.Column(db.Float)
    wo_number = db.Column(db.String, nullable=False)
    planned_set_time = db.Column(db.Integer)
    setup_scrap = db.Column(db.Integer)
    planned_run_time = db.Column(db.Integer)
    planned_quantity = db.Column(db.Integer)
    planned_cycle_time = db.Column(db.Integer)
    actual_quantity = db.Column(db.Integer)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_session_id = db.Column(db.Integer, db.ForeignKey('user_session.id'), nullable=False)
    active = db.Column(db.Boolean)  # This should either be true or null

    activities = db.relationship('Activity', backref='job')

    def __repr__(self):
        return f"<Job {self.wo_number} (ID {self.id})>"


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'), nullable=False)
    machine_state = db.Column(db.Integer, nullable=False)
    timestamp_start = db.Column(db.Float, nullable=False)
    timestamp_end = db.Column(db.Float)
    explanation_required = db.Column(db.Boolean)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"<Activity machine:{self.machine_id} machine_state:{self.machine_state} (ID {self.id})>"


class ScheduledActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    scheduled_machine_state = db.Column(db.Integer, nullable=False)
    timestamp_start = db.Column(db.Float, nullable=False)
    timestamp_end = db.Column(db.Float)


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
    unique = db.Column(db.String, db.CheckConstraint('1'), primary_key=True, default="1")
    dashboard_update_interval_s = db.Column(db.Integer)
    threshold = db.Column(db.Integer)


    def __repr__(self):
        return f"<Settings threshold:'{self.threshold}'>"


