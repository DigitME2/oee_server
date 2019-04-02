from flask import Blueprint

bp = Blueprint('api', __name__)

# noinspection PyPep8
from app.api import routes
