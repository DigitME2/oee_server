from flask import Blueprint

bp = Blueprint('testing', __name__)

from app.testing import routes
