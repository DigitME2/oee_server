from flask import Blueprint

bp = Blueprint('documentation', __name__)

# noinspection PyPep8
from app.documentation import routes
