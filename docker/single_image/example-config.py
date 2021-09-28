import logging
import os


class Config(object):

    # Run the server in a demo mode, with fake data and an intro screen
    DEMO_MODE = os.environ.get('DEMO_MODE') or True
    # Frequency to run machine simulations (switching activities, starting jobs etc)
    DATA_SIMULATION_FREQUENCY_SECONDS = os.environ.get('DATA_SIMULATION_FREQUENCY_SECONDS') or 60
    # The number of days of data simulation to run in the past on cold startup
    DAYS_BACKFILL = os.environ.get("DAYS_BACKFILL") or 3

    # SQLite database
    db_path = '/data/prod.db'
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    SQLALCHEMY_ECHO = False

    SECRET_KEY = os.environ.get('SECRET_KEY') or "ysd7o323kuD"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.realpath(os.path.join('../../app', 'static', 'uploads'))

    REDIS_ADDRESS = "redis://redis:6379"

    if not os.path.exists('../../logs'):
        os.mkdir('../../logs')
    FLASK_LOG_FILE = os.path.join('../../logs', 'oee_app.log')
    STREAM_LOGGING_LEVEL = logging.INFO
    FILE_LOGGING_LEVEL = logging.INFO
    ROTATING_LOG_FILE_MAX_BYTES = 1024000
    ROTATING_LOG_FILE_COUNT = 10
    LOG_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

    # The database IDs for activity codes
    NO_USER_CODE_ID = 1
    UNEXPLAINED_DOWNTIME_CODE_ID = 2
    UPTIME_CODE_ID = 3  # Preferably 0 to keep it on the bottom of the graph
    SETTING_CODE_ID = 4

    MACHINE_STATE_OFF = 0
    MACHINE_STATE_RUNNING = 1
