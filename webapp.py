import logging
import os
import threading
from app import create_app

# Create the flask app
app = create_app()

# If run by gunicorn, set the loggers to match the gunicorn loggers (which can be set with --log-level)
if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
    print("Copying Gunicorn logger settings")
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
