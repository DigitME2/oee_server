import json

from datetime import timedelta
from app import db
from app.login import bp
from app.login.forms import LoginForm
from app.login.models import User, create_default_users
from flask import render_template, request, flash, redirect, url_for, current_app, abort
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse

#todo finish

NO_JOB_RESULT_CODE = 8001

"""The screen to log the user into the system."""
current_app.logger.debug("Login attempt to /androidlogin")
response = {}
if "user_id" in request.get_json():
    user_id = request.get_json()["user_id"]
    user = User.query.get(user_id)
    if user is None:
        response["success"] = False
@bp.route('/checkstate', methods=['GET'])
def android_check_state():
    current_app.logger.debug(f"State check from {request.remote_addr}")
    return "no_user"

@bp.route('/androidlogin', methods=['POST'])
def android_login():
    if True: #todo
        response["reason"] = f"User {user_id} does not exist"
        return json.dumps(response), 200, {'ContentType': 'application/json'}
    else:
        response["success"] = False
        response["reason"] = "No user_id supplied"
        return json.dumps(response), 200, {'ContentType': 'application/json'}

    if "password" in request.get_json():
        password = request.get_json()["password"]
    else:
        response["success"] = False
        response["reason"] = "No password supplied"
        return json.dumps(response), 200, {'ContentType': 'application/json'}

    if user.check_password(password):
        current_app.logger.info(f"Logged in {user} (Android)")
        response["success"] = True
        response["user_state"] = NO_JOB_RESULT_CODE  # TODO implement result codes
        login_user(user)  # TODO I don't think the user is logged in when using android, need to remove this or make it work
        return json.dumps(response), 200, {'ContentType': 'application/json'}

    else:
        response["success"] = False
        response["reason"] = "Wrong password"
        print("authentication failure")
        return json.dumps(response), 200, {'ContentType': 'application/json'}



    #todo When logging in and logging out, set the machine accordingly


@bp.route('/androidlogout', methods=['POST'])
@login_required
def android_logout():
    """ Logs the user out of the system. """
    current_app.logger.info(f"Logging out {current_user}")
    logout_user()
    return redirect("100")






