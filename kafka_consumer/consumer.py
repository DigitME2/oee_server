import logging
import os
import sys

from app import file_handler, stream_handler
from app.default.models import MACHINE_STATE_RUNNING, UPTIME_CODE_ID, UNEXPLAINED_DOWNTIME_CODE_ID
from config import Config
from logging.handlers import RotatingFileHandler
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable


engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Base = declarative_base(engine)
metadata = Base.metadata
Session = sessionmaker(bind=engine)
session = Session()


# Set up logger
logger = logging.getLogger('kafka_consumer')
logger.setLevel(logging.DEBUG)
if not os.path.exists('logs'):
    os.mkdir('logs')

# Add the handlers from the flask app
logger.addHandler(stream_handler)
logger.addHandler(file_handler)


def consumer_thread():
    """ Runs a kafka consumer"""

    # Get Kafka settings from Config file
    topic = Config.KAFKA_TOPIC
    bootstrap_servers = Config.KAFKA_BOOTSTRAP_SERVERS
    group_id = Config.KAFKA_GROUP_ID

    logger.info("Starting Kafka Consumer")
    logger.info(f" - Topic: {topic}")
    logger.info(f" - Bootstrap servers: {bootstrap_servers}")
    logger.info(f" - Group ID: {group_id}")

    # Start the Kafka consumer
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id=group_id)
    except NoBrokersAvailable:
        logger.error("No Kafka broker found")
        return

    # Handle published messages
    for message in consumer:
        logger.info(f"Message published on {message.topic}:{message.value}")
        create_new_activity(message)


class Activity(Base):
    """Auto loads the table details for the activity table from the database.
    This file does not use the database context from the flask app, which allows it to be run independently"""
    __tablename__ = 'activity'
    __table_args__ = {'autoload': True}

    def __repr__(self):
        return f"<Activity machine:{self.machine_id} machine_state:{self.machine_state} (ID {self.id})>"


def create_new_activity(message):
    """ Creates an activity from a topic message and saves it to database"""
    # Extract the data from the message
    try:
        timestamp_start = message.timestamp/1000
        params = message.value.decode("utf-8").split(sep="_")
        machine_id = params[0]
        new_machine_state = params[1]
    except:
        logger.error("Bad topic format in message", exc_info=True)
        return

    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=machine_id, timestamp_end=timestamp_start)

    try:
        # Translate machine state into activity code
        if int(new_machine_state) == MACHINE_STATE_RUNNING:
            activity_id = UPTIME_CODE_ID
        else:
            activity_id = UNEXPLAINED_DOWNTIME_CODE_ID

        new_activity = Activity()
        new_activity.machine_id = machine_id
        new_activity.machine_state = new_machine_state
        new_activity.activity_code_id = activity_id
        new_activity.timestamp_start = timestamp_start

        session.add(new_activity)
        session.commit()
        logger.debug(f"Started {new_activity}")

    except:
        logger.error("Bad machine state in topic message", exc_info=True)


def complete_last_activity(machine_id, timestamp_end):
    """ Gets the current active activity for a machine and then ends it with the current time"""
    current_activity = get_current_activity(machine_id)
    if current_activity is None:
        logging.info("No current activity found")
        return
    current_activity.timestamp_end = timestamp_end
    session.commit()
    logger.debug(f"Ended {current_activity}")


def get_current_activity(machine_id):
    """ Get the current activity of a machine"""
    # Get all activities without an end time
    # noinspection PyComparisonWithNone
    activities = session.query(Activity).filter(Activity.machine_id == machine_id, Activity.timestamp_end == None).all()

    if len(activities) == 0:
        return None

    elif len(activities) == 1:
        return activities[0]

    else:
        # If there is more than one activity without an end time, print a warning and return the most recent
        logging.warn("More than one open-ended activity when trying to get current activity:")
        for act in activities:
            logging.warn(act)
        current_activity = activities[0]
        logging.warn(f"Using {current_activity}")
        for act in activities:
            if act.timestamp_start > current_activity.timestamp_start:
                current_activity = act
        return current_activity


if __name__ == "__main__":
    consumer_thread()

