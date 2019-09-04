from datetime import timedelta
from app import db
from app.login import bp
from app.login.forms import LoginForm
from app.login.models import User, create_default_users
from flask import render_template, request, flash, redirect, url_for, current_app, session
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse

#todo i only just started on this file

@bp.route('/androidlogin', methods=['GET', 'POST'])
def login():
    """The screen to log the user into the system."""
    # call create_all to create database tables if this is the first run
    db.create_all()
    # If there are no users, create a default admin and non-admin
    if len(User.query.all()) == 0:
        create_default_users()
    # Redirect the user if already logged in
    if current_user.is_authenticated:
        # redirect if already logged in
        return "103"  # TODO Need a way to indicate already logged in and hand the user

    if request.method == 'POST':
        # Check the password and log the user in
        user = User() #todo
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for('login.login'))
        login_user(user)
        current_app.logger.info(f"Logged in {user}")
        # If the user was redirected here, send the user back to the original page
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            # If no next page given, default to these pages
            if user.admin:
                next_page = url_for('oee_displaying.multiple_machine_graph')
            else:
                next_page = url_for('oee_monitoring.production')
        return redirect(next_page)
    nav_bar_title = "Login"
    return "100"

    #todo When logging in and logging out, set the machine accordingly


@bp.route('/androidlogout', methods=['POST'])
@login_required
def logout():
    """ Logs the user out of the system. """
    current_app.logger.info(f"Logging out {current_user}")
    logout_user()
    return redirect("100")







