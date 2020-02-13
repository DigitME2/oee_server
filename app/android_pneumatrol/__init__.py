from flask import Blueprint

bp = Blueprint('android_login', __name__)

# noinspection PyPep8
from app.android_pneumatrol import routes
