import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask.logging import default_handler
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from config import Config

# Set up logging handlers
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler(filename=Config.FLASK_LOG_FILE, maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'))
stream_handler = logging.StreamHandler()
if os.environ.get('FLASK_DEBUG') == '1':
    stream_handler.setLevel(logging.DEBUG)
    file_handler.setLevel(logging.DEBUG)
else:
    stream_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)


# Use seconds in the graphs and measurements. Useful in debugging
if os.environ.get('USE_SECONDS') == 'True':
    USE_SECONDS = True
else:
    USE_SECONDS = False


db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login.login'


# Set up Kafka producer to publish messages to Kafka
topic = Config.KAFKA_TOPIC
bootstrap_servers = Config.KAFKA_BOOTSTRAP_SERVERS


def create_app(config_class=Config):
    app = Flask(__name__)

    # Set up logger
    app.logger.setLevel(logging.DEBUG)
    app.logger.removeHandler(default_handler)
    app.logger.addHandler(stream_handler)
    app.logger.addHandler(file_handler)

    app.config.from_object(config_class)
    db.init_app(app)
    # Fill the database with default values
    with app.app_context():
        from app.setup_database import setup_database
        setup_database()

    login_manager.init_app(app)

    # Start the Kafka producer
    app.producer = KafkaProducer(bootstrap_servers=bootstrap_servers)


    from app.admin import bp as admin_bp
    from app.default import bp as default_bp
    from app.errors import bp as errors_bp
    from app.login import bp as users_bp
    from app.oee_displaying import bp as oee_displaying_bp
    from app.oee_monitoring import bp as oee_monitoring_bp
    from app.testing import bp as testing_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(default_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(oee_displaying_bp)
    app.register_blueprint(oee_monitoring_bp)
    app.register_blueprint(testing_bp)

    # api blueprint allows app to create activities via REST
    # app.register_blueprint(api_bp)
    # from app.api import bp as api_bp

    app.logger.info(f"USE_SECONDS = {os.environ.get('USE_SECONDS')}")
    app.logger.info(f"DEMO_MODE = {os.environ.get('DEMO_MODE')}")

    return app
