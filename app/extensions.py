from celery import Celery
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login.login'
celery_app = Celery('tasks', broker=Config.REDIS_ADDRESS, backend=Config.REDIS_ADDRESS)
