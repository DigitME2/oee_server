from flask import Blueprint

bp = Blueprint('oee_monitoring', __name__)

# noinspection PyPep8
from app.oee_monitoring import routes
