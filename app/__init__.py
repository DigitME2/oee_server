import logging
import os
from logging.handlers import RotatingFileHandler
import logging.config
from pathlib import Path
from time import strftime

from flask import Flask, request
from flask.logging import default_handler
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import db, migrate, login_manager, celery_app
from config import Config

VERSION = "v7.3"

# Set up logging handlers
Path('logs').mkdir(parents=True, exist_ok=True)
logging.config.fileConfig(fname='logging.conf', disable_existing_loggers=True)
get_logger = logging.getLogger("get")
post_logger = logging.getLogger("post")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config['LOGIN_DISABLED'] = False

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
    celery_app.conf.update(app.config)

    from app.admin import bp as admin_bp
    from app.api import bp as api_bp
    from app.default import bp as default_bp
    from app.documentation import bp as doc_bp
    from app.errors import bp as errors_bp
    from app.login import bp as users_bp
    from app.visualisation import bp as oee_displaying_bp
    from app.android import bp as android_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(default_bp)
    app.register_blueprint(doc_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(oee_displaying_bp)
    app.register_blueprint(android_bp)

    @app.before_first_request
    def initial_setup():
        with app.app_context():
            # Fill the database with default values
            from app.setup_database import setup_database
            if not Config.TESTING:
                setup_database()

            from app.default.db_helpers import backfill_missed_schedules
            backfill_missed_schedules()

            if Config.DEMO_MODE:
                from app.demo.machine_simulator import backfill_missed_simulations
                backfill_missed_simulations()

    # Function to log requests
    @app.after_request
    def request_logger(response):
        if response.status_code in [200, 302, 304]:
            app.logger.debug(f'{request.method} {request.full_path} {response.status_code}')
        else:
            app.logger.warning(f'{request.method} {request.full_path} {response.status_code}')
        if request.method == "POST":
            post_logger.info(f'{request.full_path}')
        return response

    # Allows templates to know whether the app is running in demo mode
    @app.context_processor
    def is_demo_mode():
        return {"demo_mode": Config.DEMO_MODE}

    return app
