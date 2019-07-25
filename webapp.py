import logging
import os
import threading
from app import create_app
from kafka_consumer.consumer import consumer_thread


# Create the flask app
app = create_app()

# If run by gunicorn, set the loggers to match the gunicorn loggers (which can be set with --log-level)
if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
    print("Copying Gunicorn logger settings")
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Start a thread to subscribe to kafka
# todo uncomment. this is left commented because its a faff to end if its launched from the main thread
#kafka_consumer = threading.Thread(target=consumer_thread)
#kafka_consumer.start()
