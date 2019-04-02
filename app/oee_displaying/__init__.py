from flask import Blueprint

bp = Blueprint('oee_displaying', __name__)

# noinspection PyPep8
from app.oee_displaying import routes
