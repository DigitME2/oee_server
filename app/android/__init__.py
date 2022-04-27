from flask import Blueprint

bp = Blueprint('android', __name__)

# noinspection PyPep8
from app.android import routes_default, routes_pausable, routes_running_total
