import logging
import math as maths
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from random import randrange
from time import time

from sqlalchemy import create_engine
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import Config

# TODO can move this file back to somewhere with app context

# Set up logger
logger = logging.getLogger('machine_activity')
logger.setLevel(logging.DEBUG)
file_handler = RotatingFileHandler(filename=Config.FLASK_LOG_FILE, maxBytes=10240, backupCount=10)
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
# This file does not use the database context from the flask app, allowing it to be run independently
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Base = declarative_base(engine)
metadata = Base.metadata
Session = sessionmaker(bind=engine)


try:
    class Machine(Base):
        """Auto loads the table details for the machine table from the database."""
        __tablename__ = 'machine'
        __table_args__ = {'autoload': True}

        def __repr__(self):
            return f"<Machine '{self.name}' (ID {self.id})"
except NoSuchTableError:
    logger.warning("No Machine Table")


try:
    class Activity(Base):
        """Auto loads the table details for the activity table from the database."""
        __tablename__ = 'activity'
        __table_args__ = {'autoload': True}

        def __repr__(self):
            return f"<Activity machine:{self.machine_id} machine_state:{self.machine_state} (ID {self.id})>"
except NoSuchTableError:
    logger.warning("No Activity Table")


try:
    class ScheduledActivity(Base):
        """Auto loads the table details for the activity table from the database."""
        __tablename__ = 'scheduled_activity'
        __table_args__ = {'autoload': True}

        def __repr__(self):
            return f"<ScheduledActivity machine:{self.machine_id} scheduled_machine_state:{self.scheduled_machine_state} (ID {self.id})>"
except NoSuchTableError:
    logger.warning("No ScheduledActivity Table")


def complete_last_activity(machine_id, timestamp_end=None):
    """ Gets the most recent active activity for a machine and then ends it with the current time, or a provided time"""

    # Don't put datetime.now() as the default argument, it will break this function
    if timestamp_end is None:
        timestamp_end = datetime.now().timestamp()
    session = Session()
    last_activity_id = get_current_activity_id(machine_id)
    if last_activity_id is None:
        return
    last_activity = session.query(Activity).get(last_activity_id)
    last_activity.timestamp_end = timestamp_end
    session.commit()
    logger.debug(f"Ended {last_activity}")
    session.close()


def get_current_activity_id(target_machine_id):
    """ Get the current activity of a machine by grabbing the most recent entry without an end timestamp"""
    session = Session()
    # Get all activities without an end time
    # noinspection PyComparisonWithNone
    # The line below is causing a sql.programmingerror and im not sure why
    activities = session.query(Activity).filter(Activity.machine_id == target_machine_id, Activity.timestamp_end == None).all()
    session.close()
    if len(activities) == 0:
        logger.debug(f"No current activity on machine ID {target_machine_id}")
        return None

    elif len(activities) == 1:
        logger.debug(f"Current activity for machine ID {target_machine_id} -> {activities[0]}")
        return activities[0].id

    else:
        # If there is more than one activity without an end time, end them and return the most recent

        # Get the current activity by grabbing the one with the most recent start time
        current_activity = max(activities, key=lambda activity: activity.timestamp_start)
        activities.remove(current_activity)

        logger.warning("More than one open-ended activity when trying to get current activity:")
        for act in activities:
            if act.timestamp_end == None:
                logger.warning(f"Closing lost activity {act}")
                act.timestamp_end = act.timestamp_start
                session.add(act)
                session.commit()

        return current_activity.id


def flag_activities(activities, threshold):
    """ Filters a list of activities, adding explanation_required=True to those that require an explanation
    for downtime above a defined threshold"""
    session = Session()
    ud_index_counter = 0
    downtime_explanation_threshold_s = threshold
    for act in activities:
        # Only Flag activities with the downtime code and with a duration longer than the threshold
        if act.activity_code_id == Config.UNEXPLAINED_DOWNTIME_CODE_ID and \
                (act.timestamp_end - act.timestamp_start) > downtime_explanation_threshold_s:
            act.explanation_required = True
            # Give the unexplained downtimes their own index
            act.ud_index = ud_index_counter
            ud_index_counter += 1
        else:
            act.explanation_required = False
    session.commit()
    session.close()
    return activities


def split_activity(activity_id, split_time=None):
    """ Ends an activity and starts a new activity with the same values, ending/starting at the split_time"""
    session = Session()
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
    session.close()


# noinspection PyArgumentList
def get_dummy_machine_activity(timestamp_start, timestamp_end, job_id, machine_id):
    """ Creates fake activities for one machine between two timestamps"""
    virtual_time = timestamp_start
    activities = []
    while virtual_time <= timestamp_end:
        uptime_activity = Activity(machine_id=machine_id,
                                   timestamp_start=virtual_time,
                                   machine_state=Config.MACHINE_STATE_RUNNING,
                                   activity_code_id=Config.UPTIME_CODE_ID,
                                   job_id=job_id)
        virtual_time += randrange(400, 3000)
        uptime_activity.timestamp_end = virtual_time
        activities.append(uptime_activity)

        downtime_activity = Activity(machine_id=machine_id,
                                     timestamp_start=virtual_time,
                                     machine_state=Config.MACHINE_STATE_OFF,
                                     activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                                     job_id=job_id)
        virtual_time += randrange(60, 1000)
        downtime_activity.timestamp_end = virtual_time
        activities.append(downtime_activity)

    return activities


def create_daily_scheduled_activities(skip_if_already_done=True):
    session = Session()
    logger.info(f"Creating Scheduled Activities")
    for machine in session.query(Machine).all():
        # TODO Check if today's activities have already been created

        logger.debug(f"Creating Scheduled Activities for {machine}")

        last_midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        next_midnight = last_midnight + timedelta(days=1)

        # Check to see if activities have already been created for today
        # noinspection PyUnresolvedReferences
        existing_activities = session.query(ScheduledActivity) \
            .filter(ScheduledActivity.machine_id == machine.id) \
            .filter(ScheduledActivity.timestamp_start > last_midnight.timestamp()) \
            .filter(ScheduledActivity.timestamp_end < next_midnight.timestamp()).all()

        if skip_if_already_done and len(existing_activities) > 0:
            logger.warn(f"Scheduled activities already exist today for {machine} Skipping...")
            continue

        # noinspection PyArgumentList
        morning = ScheduledActivity(machine_id=machine.id,
                                    scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                    timestamp_start=last_midnight.timestamp(),
                                    timestamp_end=decimal_time_to_current_day(machine.schedule_start_1))

        # noinspection PyArgumentList
        shift1 = ScheduledActivity(machine_id=machine.id,
                                   scheduled_machine_state=Config.MACHINE_STATE_RUNNING,
                                   timestamp_start=decimal_time_to_current_day(machine.schedule_start_1),
                                   timestamp_end=decimal_time_to_current_day(machine.schedule_end_1))

        # noinspection PyArgumentList
        break1 = ScheduledActivity(machine_id=machine.id,
                                   scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                   timestamp_start=decimal_time_to_current_day(machine.schedule_end_1),
                                   timestamp_end=decimal_time_to_current_day(machine.schedule_start_2))

        # noinspection PyArgumentList
        shift2 = ScheduledActivity(machine_id=machine.id,
                                   scheduled_machine_state=Config.MACHINE_STATE_RUNNING,
                                   timestamp_start=decimal_time_to_current_day(machine.schedule_start_2),
                                   timestamp_end=decimal_time_to_current_day(machine.schedule_end_2))
        # noinspection PyArgumentList
        break2 = ScheduledActivity(machine_id=machine.id,
                                   scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                   timestamp_start=decimal_time_to_current_day(machine.schedule_end_2),
                                   timestamp_end=decimal_time_to_current_day(machine.schedule_start_3))

        # noinspection PyArgumentList
        shift3 = ScheduledActivity(machine_id=machine.id,
                                   scheduled_machine_state=Config.MACHINE_STATE_RUNNING,
                                   timestamp_start=decimal_time_to_current_day(machine.schedule_start_3),
                                   timestamp_end=decimal_time_to_current_day(machine.schedule_end_3))

        # noinspection PyArgumentList
        night = ScheduledActivity(machine_id=machine.id,
                                  scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                  timestamp_start=decimal_time_to_current_day(machine.schedule_end_3),
                                  timestamp_end=next_midnight.timestamp())

        session.add(morning)
        session.add(shift1)
        session.add(break1)
        session.add(shift2)
        session.add(break2)
        session.add(shift3)
        session.add(night)
        session.commit()
        session.close()


def decimal_time_to_current_day(decimal_time):
    """ Turns decimal time for an hour (ie 9.5=9.30am) into a timestamp for the given time on the current day"""
    hour = maths.floor(decimal_time)
    minute = (decimal_time - hour) * 60
    return datetime.now().replace(hour=hour, minute=minute).timestamp()


def get_activity_duration(activity_id):
    """ Gets the duration of an activity in minutes"""
    session = Session()
    act = session.query(Activity).get(activity_id)
    start = act.timestamp_start
    if act.timestamp_end is not None:
        end = act.timestamp_end
    else:
        end = datetime.now().timestamp()
    return (end - start)/60


def get_legible_duration(timestamp_start, timestamp_end):
    """ Takes two timestamps and returns a string in the format <hh:mm> <x> minutes"""
    minutes = maths.floor((timestamp_end - timestamp_start) / 60)
    hours = maths.floor((timestamp_end - timestamp_start) / 3600)
    if minutes == 0:
        return f"{maths.floor(timestamp_end - timestamp_start)} seconds"
    if hours == 0:
        return f"{minutes} minutes"
    else:
        leftover_minutes = minutes - (hours * 60)
        return f"{hours} hours {leftover_minutes} minutes"

