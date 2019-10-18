import logging
import os


class Config(object):

    # # Get the database details from environment variables
    # DATABASE_USER = os.environ.get('DATABASE_USER') or "postgres"
    # DATABASE_ADDRESS = os.environ.get('DATABASE_ADDRESS') or "localhost"
    # DATABASE_PORT = os.environ.get('DATABASE_PORT') or "5432"
    # DATABASE_NAME = os.environ.get('DATABASE_NAME') or "webapp"
    #
    # print("Database: {database} at {address}:{port}".format(
    #     address=DATABASE_ADDRESS,
    #     port=DATABASE_PORT,
    #     database=DATABASE_NAME))
    #
    # # If no password is given, prompt the user to type it in
    # DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD') or \
    #                     getpass.getpass(prompt="Enter password ({user}):".format(user=DATABASE_USER))
    #
    #
    # SQLALCHEMY_DATABASE_URI = "postgres://{user}:{password}@{address}:{port}/{database}".format(
    #     user=DATABASE_USER,
    #     password=DATABASE_PASSWORD,
    #     address=DATABASE_ADDRESS,
    #     port=DATABASE_PORT,
    #     database=DATABASE_NAME)

    package_dir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(package_dir, 'app', 'prod.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

    SECRET_KEY = os.environ.get('SECRET_KEY') or "yS7o773kuQ"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.realpath(os.path.join('app', 'static', 'uploads'))

    if not os.path.exists('logs'):
        os.mkdir('logs')

    STREAM_LOGGING_LEVEL = logging.DEBUG
    FILE_LOGGING_LEVEL = logging.DEBUG
    FLASK_LOG_FILE = 'logs/oee_app.log'
    LOG_FORMATTER = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')

    NO_USER_CODE_ID = 1
    UNEXPLAINED_DOWNTIME_CODE_ID = 2  # The ID of the activity code that represents unexplained downtime
    UPTIME_CODE_ID = 3  # The ID of the activity code that for uptime. Preferably 0 to keep it on the bottom of the graph
    SETTING_CODE_ID = 4
    MACHINE_STATE_OFF = 0
    MACHINE_STATE_RUNNING = 1