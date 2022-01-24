from flask import Blueprint

bp = Blueprint('android_pausable', __name__)

# noinspection PyPep8
from app.android_pausable import routes
