from app import db

UNEXPLAINED_DOWNTIME_CODE_ID = 0  # The ID of the activity code that represents unexplained downtime
UPTIME_CODE_ID = 1  # The ID of the activity code that represents uptime

MACHINE_STATE_OFF = 0
MACHINE_STATE_RUNNING = 1
MACHINE_STATE_ERROR = 2


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
    machine_state = db.Column(db.Integer, nullable=False)
    explanation_required = db.Column(db.Boolean)
    timestamp_start = db.Column(db.Integer, nullable=False)
    timestamp_end = db.Column(db.Integer)
    activity_code_id = db.Column(db.Integer, db.ForeignKey('activity_code.id'))
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))


class ActivityCode(db.Model):
    """ Holds the codes to identify activities"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String, unique=True)
    short_description = db.Column(db.String)
    long_description = db.Column(db.String)
    graph_colour = db.Column(db.String)

    activities = db.relationship('Activity', backref='activity_code')


