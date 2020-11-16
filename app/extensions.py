from celery import Celery
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login.login'
celery_app = Celery('tasks', broker='redis://localhost:6379', backend='redis://localhost:6379')


@celery_app.task
def task1():
    print("running task 1")
    return