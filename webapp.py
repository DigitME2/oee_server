from app import create_app
from kafka_consumer.consumer import consumer_thread
import logging
import threading

# Create the flask app
app = create_app()

# If run by gunicorn, set the loggers to match the gunicorn loggers (which can be set with --log-level)
if __name__ != "__main__":
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Start a thread to subscribe to kafka
#kafka_consumer = threading.Thread(target=consumer_thread)
#kafka_consumer.start()
