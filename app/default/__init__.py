from flask import Blueprint

bp = Blueprint('default', __name__)

from app.default import routes