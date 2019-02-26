from flask import Blueprint

bp = Blueprint('oee_displaying', __name__)

from app.oee_displaying import routes
