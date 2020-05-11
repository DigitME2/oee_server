import logging

from app import db

logger = logging.getLogger('flask.app')


class DailyOEE(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer)
    date = db.Column(db.Date)
    oee = db.Column(db.Float)


