from flask import Blueprint

bp = Blueprint('prod_recording', __name__)

from app.prod_recording import models, routes
