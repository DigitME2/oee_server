from flask import Blueprint

bp = Blueprint('oee_monitoring', __name__)

from app.oee_monitoring import models, routes
