from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'login.login'
if Config.ENABLE_KAFKA:
    from kafka import KafkaProducer
    kafka_producer = KafkaProducer(bootstrap_servers=Config.KAFKA_ADDRESS + ":" + Config.KAFKA_PORT)
