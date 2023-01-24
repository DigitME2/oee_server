from flask import Blueprint

bp = Blueprint('default', __name__)

# noinspection PyPep8,PyPep8
from app.default import routes