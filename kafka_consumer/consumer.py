import logging
import os
from app.oee_monitoring.helpers import create_new_activity, complete_last_activity, get_current_activity
from config import Config
from logging.handlers import RotatingFileHandler
from time import sleep
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable


# Set up logger
logger = logging.getLogger('kafka_consumer')
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(filename=Config.KAFKA_LOG_FILE, maxBytes=10240, backupCount=10)
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
    consumer = None
    while consumer is None:
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap_servers,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id=group_id)
        except NoBrokersAvailable:
            logger.error("No Kafka broker found (Retry in 5s)")
            sleep(5)

        logger.info(f"Connected to Kafka broker")

    # Handle published messages
    for message in consumer:
        logger.info(f"Message published on {message.topic}:{message.value.decode('utf-8')}")
        message_handler(message)


def message_handler(message):

    try:
        # Extract the data from the message
        timestamp_start = message.timestamp / 1000
        params = message.value.decode("utf-8").split(sep="_")
    except:
        logger.error("Bad machine state in topic message", exc_info=True)
        return
    try:
        machine_id = int(params[0])
        new_machine_state = int(params[1])
    except(ValueError, IndexError):
        logger.error(f"Bad format in message '{message.value.decode('utf-8')}'")
        return

    # Mark the most recent activity in the database as complete
    complete_last_activity(machine_id=machine_id, timestamp_end=timestamp_start)

    # Start a new activity
    create_new_activity(machine_id=machine_id, machine_state=new_machine_state, timestamp_start=timestamp_start)


if __name__ == "__main__":
    consumer_thread()

