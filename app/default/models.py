import logging

from app import db

logger = logging.getLogger('flask.app')


class Machine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    group = db.Column(db.String)
    device_ip = db.Column(db.String, unique=True)
    active = db.Column(db.Boolean, default=True)
    # Schedule times are saved as decimal time e.g. 9.5 - 9.30am
    schedule_start_1 = db.Column(db.Integer)
    schedule_end_1 = db.Column(db.Integer)
    schedule_start_2 = db.Column(db.Integer)
    schedule_end_2 = db.Column(db.Integer)
    schedule_start_3 = db.Column(db.Integer)
    schedule_end_3 = db.Column(db.Integer)

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
    wo_number = db.Column(db.String, nullable=False)
    planned_set_time = db.Column(db.Integer)
    planned_cycle_time = db.Column(db.Integer)
    planned_cycle_quantity = db.Column(db.Integer)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    active = db.Column(db.Boolean)  # This should either be true or null

    activities = db.relationship('Activity', backref='job')

    def __repr__(self):
        return f"<Job {self.wo_number} (ID {self.id})>"


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.String, db.ForeignKey('machine.id'), nullable=False)
    machine_state = db.Column(db.Integer, nullable=False)
    scheduled_state = db.Column(db.Integer)
    explanation_required = db.Column(db.Boolean)
    timestamp_start = db.Column(db.Float, nullable=False)
    timestamp_end = db.Column(db.Float)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'))
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
    threshold = db.Column(db.Integer)

    def __repr__(self):
        return f"<Settings threshold:'{self.threshold}'>"


