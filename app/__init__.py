from config import Config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager


db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.default import bp as default_bp
    from app.login import bp as users_bp
    from app.errors import bp as errors_bp
    from app.oee_monitoring import bp as oee_monitoring_bp

    app.register_blueprint(default_bp)
    app.register_blueprint(errors_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(oee_monitoring_bp)

    return app
