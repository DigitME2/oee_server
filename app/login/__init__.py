from flask import Blueprint

bp = Blueprint('login', __name__)

# noinspection PyPep8
from app.login import models, routes, session_recorder

