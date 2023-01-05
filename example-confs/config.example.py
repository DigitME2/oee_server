import os
from distutils.util import strtobool


class Config(object):

    """ ------- Run mode ------- """
    # Set during testing
    TESTING = strtobool(os.environ.get("TESTING", "false"))
    # Run the server in a demo mode, with fake data and an intro screen
    DEMO_MODE = strtobool(os.environ.get("DEMO_MODE", "false"))

    """ ------- Database settings ------- """
    # SQLite database
    db_name = "prod.db"
    if DEMO_MODE:
        db_name += "prod_demo.db"
    package_dir = os.path.abspath(os.path.dirname(__file__))
    if TESTING:
        db_name = "test.db"
        db_path = os.path.join(package_dir, "app", "testing", db_name)
    else:
        db_path = os.path.join(package_dir, db_name)
    SQLITE_STRING = f"sqlite:///{db_path}" + '?check_same_thread=False'
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Set this to use postgres or sql-server string if needed (example code at bottom of this file)
    SQLALCHEMY_DATABASE_URI = SQLITE_STRING

    """ ------- Job Validation settings ------- """
    # Allow job numbers to be checked against a database when being entered into the tablet. Prompts the user if wrong
    USE_JOB_VALIDATION = False
    # If two columns are given here, jobs will be checked against the first column. The second column will be displayed
    # to the user when a matching job number is entered
    # SECOND_DATABASE_ODBC_STRING = SQLITE_STRING
    # JOB_VALIDATION_SQL_STRING = "SELECT job_number, description FROM active_jobs;"

    """ ------- Misc settings ------- """
    SECRET_KEY = os.environ.get('SECRET_KEY') or "change-this-secret-key"
    UPLOAD_FOLDER = os.path.realpath(os.path.join('app', 'static', 'uploads'))
    EXTERNAL_PORT = "80"
    REDIS_HOST = "localhost"
    REDIS_PORT = "6379"

    """ ------- Kafka settings ------- """
    ENABLE_KAFKA = True
    KAFKA_ADDRESS = "localhost"
    KAFKA_PORT = "9092"

    """ OEE server settings"""
    WORKFLOW_TYPES = ["default", "pausable", "running_total"]

    # The database IDs for activity codes
    UPTIME_CODE_ID = 1
    UNEXPLAINED_DOWNTIME_CODE_ID = 2

    # Categories for activity codes
    DOWNTIME_CATEGORIES = [("none", "None"),
                           ("machine_error", "Machine error"),
                           ("operator_error", "Operator error"),
                           ("material_error", "Material error")]

    # Database ID for machine state and scheduled state
    MACHINE_STATE_UPTIME = 1
    MACHINE_STATE_UNPLANNED_DOWNTIME = 2
    MACHINE_STATE_PLANNED_DOWNTIME = 3
    MACHINE_STATE_OVERTIME = 4

    RUNNING_TOTAL_UPDATE_FREQUENCY_SECONDS = 3600

    """ Demo mode settings"""
    # Frequency to run machine simulations (switching activities, starting jobs etc.)
    DATA_SIMULATION_FREQUENCY_SECONDS = int(os.environ.get('DATA_SIMULATION_FREQUENCY_SECONDS', 60))

    # The number of days of data simulation to run in the past on cold startup
    DAYS_BACKFILL = int(os.environ.get("DAYS_BACKFILL", 3))

    # PostgreSQL database
    # DATABASE_USER = os.environ.get('DATABASE_USER')
    # DATABASE_ADDRESS = os.environ.get('DATABASE_ADDRESS')
    # DATABASE_PORT = os.environ.get('DATABASE_PORT')
    # DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD')
    # if DEMO_MODE:
    #     DATABASE_NAME = "oee_webapp_demo"
    # else:
    #     DATABASE_NAME = os.environ.get('DATABASE_NAME') or "oee"
    # POSTGRES_STRING = "postgresql://{user}:{password}@{address}:{port}/{database}".format(
    #     user=DATABASE_USER,
    #     password=DATABASE_PASSWORD,
    #     address=DATABASE_ADDRESS,
    #     port=DATABASE_PORT,
    #     database=DATABASE_NAME)

    # SQL Server database
    # from sqlalchemy.engine import URL
    # connection_string = os.environ.get('SQL_SERVER_CONNECTION_STRING') or \
    # "DRIVER=/opt/microsoft/msodbcsql18/lib64/libmsodbcsql-18.1.so.1.1;SERVER=localhost;DATABASE=oee;UID=sa;PWD=<password>;TrustServerCertificate=yes;"
    # SQL_SERVER_STRING = URL.create(
    #     "mssql+pyodbc",
    #     query={"odbc_connect": connection_string}
    # )
