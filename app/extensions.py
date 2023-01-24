import logging

from celery import Celery
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login.login'
celery_app = Celery('tasks', broker=Config.CELERY_BROKER, backend=Config.CELERY_BROKER)
if Config.ENABLE_KAFKA:
    kafka_producer = KafkaProducer(bootstrap_servers=Config.KAFKA_ADDRESS + ":" + Config.KAFKA_PORT)
