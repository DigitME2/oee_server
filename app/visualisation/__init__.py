from flask import Blueprint

bp = Blueprint('visualisation', __name__)

# noinspection PyPep8
from app.visualisation import routes
