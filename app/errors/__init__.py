from flask import Blueprint

bp = Blueprint('errors', __name__)

# noinspection PyPep8,PyPep8
from app.errors import handlers