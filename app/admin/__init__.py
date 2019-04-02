from flask import Blueprint

bp = Blueprint('admin', __name__)

# noinspection PyPep8
from app.admin import routes
