import logging
import math as maths
import os
from random import randrange
from config import Config
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from sqlalchemy import create_engine
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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





def create_new_activity(machine_id, machine_state, timestamp_start=time()):
    """ Creates an activity and saves it to database"""
    session = Session()
    # Translate machine state into activity code
    if int(machine_state) == Config.MACHINE_STATE_RUNNING:
        activity_id = Config.UPTIME_CODE_ID
    else:
        activity_id = Config.UNEXPLAINED_DOWNTIME_CODE_ID


    new_activity = Activity()
    new_activity.machine_id = machine_id
    new_activity.machine_state = machine_state
    new_activity.activity_code_id = activity_id
    new_activity.timestamp_start = timestamp_start


    session.add(new_activity)
    session.commit()
    logger.debug(f"Started {new_activity}")
    session.close()


def complete_last_activity(machine_id, timestamp_end):
    """ Gets the most recent active activity for a machine and then ends it with the current time"""
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
        # If there is more than one activity without an end time, print a warning and return the most recent
        logger.warning("More than one open-ended activity when trying to get current activity:")
        for act in activities:
            logger.debug(f"Open activity: {act}")
        current_activity = activities[0]
        logger.debug(f"Using {current_activity} as current activity")
        for act in activities:
            if act.timestamp_start < current_activity.timestamp_start:
                current_activity = act
        return current_activity.id


def get_scheduled_machine_state(machine_id, timestamp=time()):
    session = Session()
    machine = session.query(Machine).get(machine_id)

    # Calculate the decimal time
    hour = datetime.fromtimestamp(timestamp).hour
    minute = datetime.fromtimestamp(timestamp).minute
    decimal_time = hour + (minute/60)

    if machine.schedule_start_1 >= decimal_time < machine.schedule_end_1:
        pass

    session.close()


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


def create_daily_scheduled_activities():
    session = Session()
    for machine in session.query(Machine).all():
        # TODO Check if today's activities have already been created
        today = datetime.now()

        # shift_periods = ["break_1", "shift_1", "break_2", "shift_2", "break_3", "shift_3"]
        #
        # for shift in shift_periods:

        # noinspection PyArgumentList
        morning = ScheduledActivity(machine_id=machine.id,
                                    scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                    timestamp_start=datetime.now().replace(hour=0, minute=0, second=0).timestamp(),
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

        tomorrow = datetime.now() + timedelta(days=1)
        # noinspection PyArgumentList
        night = ScheduledActivity(machine_id=machine.id,
                                  scheduled_machine_state=Config.MACHINE_STATE_OFF,
                                  timestamp_start=decimal_time_to_current_day(machine.schedule_end_3),
                                  timestamp_end=tomorrow.replace(hour=0, minute=0, second=0).timestamp())

        session.add(morning)
        session.add(shift1)
        session.add(break1)
        session.add(shift2)
        session.add(break2)
        session.add(shift3)
        session.add(night)
        session.commit()

    logger.info("Creating Scheduled activities")
    #todo


def decimal_time_to_current_day(decimal_time):
    """ Turns decimal time for an hour (ie 9.5=9.30am) into a timestamp for the given time on the current day"""
    hour = maths.floor(decimal_time)
    minute = (decimal_time - hour) * 60
    return datetime.now().replace(hour=hour, minute=minute).timestamp()