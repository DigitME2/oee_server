from config import Config
from flask import Flask, current_app
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask.logging import default_handler
from logging.handlers import RotatingFileHandler
import logging
import os
import threading


# Use seconds in the graphs and measurements. Useful in debugging
if os.environ.get('USE_SECONDS') == 'True':
    USE_SECONDS = True
else:
    USE_SECONDS = False

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login.login'

# Create logging handlers
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler('logs/oee_app.log', maxBytes=10240, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'))
stream_handler = logging.StreamHandler()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    login_manager.init_app(app)

    from app.admin import bp as admin_bp
    from app.api import bp as api_bp
    from app.default import bp as default_bp
    from app.errors import bp as errors_bp
    from app.login import bp as users_bp
    from app.oee_displaying import bp as oee_displaying_bp
    from app.oee_monitoring import bp as oee_monitoring_bp
    from app.testing import bp as testing_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(default_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(oee_displaying_bp)
    app.register_blueprint(oee_monitoring_bp)
    app.register_blueprint(testing_bp)

    # Set up logger
    app.logger.setLevel(logging.DEBUG)
    if app.debug:
        stream_handler.setLevel(logging.DEBUG)
        file_handler.setLevel(logging.DEBUG)
    else:
        stream_handler.setLevel(logging.INFO)
        file_handler.setLevel(logging.INFO)

    app.logger.removeHandler(default_handler)
    app.logger.addHandler(stream_handler)
    app.logger.addHandler(file_handler)

    return app
