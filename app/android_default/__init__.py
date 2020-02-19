from flask import Blueprint

bp = Blueprint('android_default', __name__)

# noinspection PyPep8
from app.android_default import routes
