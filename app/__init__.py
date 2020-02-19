import logging
import os
from logging.handlers import RotatingFileHandler
from time import strftime

from flask import Flask, request
from flask.logging import default_handler
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.contrib.fixers import ProxyFix

from config import Config

# Set up logging handlers
if not os.path.exists('logs'):
    os.mkdir('logs')
file_handler = RotatingFileHandler(filename=Config.FLASK_LOG_FILE,
                                   maxBytes=Config.ROTATING_LOG_FILE_MAX_BYTES,
                                   backupCount=Config.ROTATING_LOG_FILE_COUNT)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'))
stream_handler = logging.StreamHandler()

stream_handler.setLevel(Config.STREAM_LOGGING_LEVEL)
file_handler.setLevel(Config.FILE_LOGGING_LEVEL)

# Use seconds in the graphs and measurements. Useful in debugging
if os.environ.get('USE_SECONDS') == 'True':
    USE_SECONDS = True
else:
    USE_SECONDS = False


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login.login'


def create_app(config_class=Config):
    app = Flask(__name__)

    # Set up logger
    app.logger.setLevel(logging.DEBUG)
    app.logger.removeHandler(default_handler)
    app.logger.addHandler(stream_handler)
    app.logger.addHandler(file_handler)

    # Add gunicorn logger
    gunicorn_logger = logging.getLogger('gunicorn.error')
    for handler in gunicorn_logger.handlers:
        app.logger.addHandler(handler)

    print("Logging level:", logging.getLevelName(app.logger.getEffectiveLevel()))

    app.config.from_object(config_class)
    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    app.wsgi_app = ProxyFix(app.wsgi_app)  # To get client IP when using a proxy

    from app.admin import bp as admin_bp
    from app.default import bp as default_bp
    from app.errors import bp as errors_bp
    from app.export import bp as export_bp
    from app.login import bp as users_bp
    from app.oee_displaying import bp as oee_displaying_bp
    from app.oee_monitoring import bp as oee_monitoring_bp
    from app.android_default import bp as android_bp
    from app.android_pneumatrol import bp as pneumatrol_bp

    if os.path.exists('app/testing'):
        from app.testing import bp as testing_bp
        app.register_blueprint(testing_bp)

    app.register_blueprint(admin_bp)
    app.register_blueprint(default_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(oee_displaying_bp)
    app.register_blueprint(oee_monitoring_bp)
    app.register_blueprint(android_bp)
    app.register_blueprint(pneumatrol_bp)

    @app.before_first_request
    def initial_setup():
        # Fill the database with default values
        with app.app_context():
            from app.setup_database import setup_database
            setup_database()

    # Function to log requests
    @app.before_request
    def before_request():
        timestamp = strftime('[%Y-%b-%d %H:%M]')
        app.logger.debug(f'{timestamp}, {request.remote_addr}, {request.method}, {request.scheme}, {request.full_path}')

    return app
