import logging
import os
from random import randrange
from app.default.models import UPTIME_CODE_ID, UNEXPLAINED_DOWNTIME_CODE_ID, MACHINE_STATE_OFF, MACHINE_STATE_RUNNING
from config import Config
from datetime import datetime
from logging.handlers import RotatingFileHandler
from sqlalchemy import create_engine
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, make_transient
from time import time


# Set up logger
logger = logging.getLogger('machine_activity')
logger.setLevel(logging.DEBUG)
file_handler = RotatingFileHandler(filename=Config.MACHINE_MONITOR_LOG_FILE, maxBytes=10240, backupCount=10)
file_handler.setFormatter(Config.LOG_FORMATTER)
stream_handler = logging.StreamHandler()
if os.environ.get('FLASK_DEBUG') == '1':
    stream_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.DEBUG)
else:
    stream_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)

# Set up database
# This module does not use flask_sqlalchemy, which requires app context
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Base = declarative_base(engine)
metadata = Base.metadata
Session = sessionmaker(bind=engine)
session = Session()

try:
    class Activity(Base):
        """Auto loads the table details for the activity table from the database.
        This file does not use the database context from the flask app, allowing it to be run independently"""
        __tablename__ = 'activity'
        __table_args__ = {'autoload': True}

        def __repr__(self):
            return f"<Activity machine:{self.machine_id} machine_state:{self.machine_state} (ID {self.id})>"
except NoSuchTableError:
    logger.warning("No Activity Table")


def create_new_activity(machine_id, machine_state, timestamp_start=time()):
    """ Creates an activity and saves it to database"""

    # Translate machine state into activity code
    if int(machine_state) == MACHINE_STATE_RUNNING:
        activity_id = UPTIME_CODE_ID
    else:
        activity_id = UNEXPLAINED_DOWNTIME_CODE_ID

    new_activity = Activity()
    new_activity.machine_id = machine_id
    new_activity.machine_state = machine_state
    new_activity.activity_code_id = activity_id
    new_activity.timestamp_start = timestamp_start

    session.add(new_activity)
    session.commit()
    logger.debug(f"Started {new_activity}")


def complete_last_activity(machine_id, timestamp_end):
    """ Gets the current active activity for a machine and then ends it with the current time"""
    current_activity = get_current_activity(machine_id)
    if current_activity is None:
        return
    current_activity.timestamp_end = timestamp_end
    session.commit()
    logger.debug(f"Ended {current_activity}")


def get_current_activity(machine_id):
    """ Get the current activity of a machine by grabbing the most recent entry without an end timestamp"""
    # Get all activities without an end time
    activities = session.query(Activity).filter(Activity.machine_id == machine_id, Activity.timestamp_end == None).all()

    if len(activities) == 0:
        logger.debug(f"No current activity on machine ID {machine_id}")
        return None

    elif len(activities) == 1:
        logger.debug(f"Current activity for machine ID {machine_id} -> {activities[0]}")
        return activities[0]

    else:
        # If there is more than one activity without an end time, print a warning and return the most recent
        logger.warning("More than one open-ended activity when trying to get current activity:")
        for act in activities:
            logger.debug(f"Open activity: {act}")
        current_activity = activities[0]
        logger.debug(f"Using {current_activity} as current activity")
        for act in activities:
            if act.timestamp_start < current_activity.timestamp_start:
                current_activity = act
        return current_activity


def flag_activities(activities, threshold):
    """ Filters a list of activities, adding explanation_required=True to those that require an explanation
    for downtime above a defined threshold"""

    ud_index_counter = 0
    downtime_explanation_threshold_s = threshold
    for act in activities:
        # Only Flag activities with the downtime code and with a duration longer than the threshold
        if act.activity_code_id == UNEXPLAINED_DOWNTIME_CODE_ID and \
                (act.timestamp_end - act.timestamp_start) > downtime_explanation_threshold_s:
            act.explanation_required = True
            # Give the unexplained downtimes their own index
            act.ud_index = ud_index_counter
            ud_index_counter += 1
        else:
            act.explanation_required = False
    session.commit()
    return activities


def split_activity(activity_id, split_time=None):
    """ Ends an activity and starts a new activity with the same values, ending/starting at the split_time"""

    old_activity = session.query(Activity).get(activity_id)

    if split_time is None:
        split_time = time()

    # Copy the old activity to a new activity
    # noinspection PyArgumentList
    new_activity = Activity(machine_id=old_activity.machine_id,
                            machine_state=old_activity.machine_state,
                            explanation_required=old_activity.explanation_required,
                            timestamp_start=split_time,
                            activity_code_id=old_activity.activity_code_id,
                            job_id=old_activity.job_id)

    # End the old activity
    old_activity.timestamp_end = split_time

    session.add(new_activity)
    session.commit()
    logger.debug(f"Ended {old_activity}")
    logger.debug(f"Started {new_activity}")


def get_legible_downtime_time(timestamp_start, timestamp_end):
    """ Takes two timestamps and returns a string in the format <hh:mm> <x> minutes"""
    start = datetime.fromtimestamp(timestamp_start).strftime('%H:%M')
    length_m = int((timestamp_end - timestamp_start) / 60)
    s = f"{start} for {length_m} minutes"

    # Show in seconds if the run time is less than a minute
    if (timestamp_end - timestamp_start) < 60:
        start = datetime.fromtimestamp(timestamp_start).strftime('%H:%M:%S')
        length_seconds = int(timestamp_end - timestamp_start)
        s = f"{start} for {length_seconds} seconds"

    return s


def get_dummy_machine_activity(timestamp_start, timestamp_end, job_id, machine_id):
    """ Creates fake activities for one machine between two timestamps"""
    time = timestamp_start
    activities = []
    while time <= timestamp_end:
        uptime_activity = Activity(machine_id=machine_id,
                                   timestamp_start=time,
                                   machine_state=MACHINE_STATE_RUNNING,
                                   activity_code_id=UPTIME_CODE_ID,
                                   job_id=job_id)
        time += randrange(400, 3000)
        uptime_activity.timestamp_end = time
        activities.append(uptime_activity)

        downtime_activity = Activity(machine_id=machine_id,
                                     timestamp_start=time,
                                     machine_state=MACHINE_STATE_OFF,
                                     activity_code_id=UNEXPLAINED_DOWNTIME_CODE_ID,
                                     job_id=job_id)
        time += randrange(60, 1000)
        downtime_activity.timestamp_end = time
        activities.append(downtime_activity)

    return activities



