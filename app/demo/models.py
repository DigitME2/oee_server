from app import db


class DemoSettings(db.Model):
    # Only allow one row in this table
    id = db.Column(db.Integer, db.CheckConstraint("id = 1"), primary_key=True)
    last_machine_simulation = db.Column(db.DateTime)
