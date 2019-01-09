from app import db, login_manager
from app.oee_monitoring.models import Job
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.oee_monitoring.models import Job


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    admin = db.Column(db.Boolean)
    active_job_id = db.Column(db.Integer)

    jobs = db.relationship('Job')

    def has_job(self):
        return self.active_job_id is not None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


def create_default_admin():
    if User.query.filter_by(username="admin").first() is not None:
        return
    default_admin = User(username="admin", admin=True)
    default_admin.set_password("password")
    db.session.add(default_admin)
    db.session.commit()
