from config import Config
from flask import Flask
from flask_login import LoginManager
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
rest_api = Api()
login_manager = LoginManager()
login_manager.login_view = 'login'


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.api import bp as api_bp
    from app.default import bp as default_bp
    from app.errors import bp as errors_bp
    from app.login import bp as users_bp
    from app.oee_displaying import bp as oee_displaying_bp
    from app.oee_monitoring import bp as oee_monitoring_bp
    from app.testing import bp as testing_bp

    rest_api.init_app(api_bp)

    app.register_blueprint(api_bp)
    app.register_blueprint(default_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(oee_displaying_bp)
    app.register_blueprint(oee_monitoring_bp)
    app.register_blueprint(testing_bp)

    return app
