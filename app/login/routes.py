from app import db
from app.login import bp
from app.login.forms import LoginForm
from app.login.models import User, create_default_users
from flask import render_template, request, flash, redirect, url_for, current_app
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """The screen to log the user into the system."""
    # call create_all to create database tables if this is the first run
    db.create_all()
    # If there are no users, create a default admin and non-admin
    if len(User.query.all()) == 0:
        create_default_users()
    # Redirect the user if already logged in
    if current_user.is_authenticated:
        # Send admins and non-admins to different pages
        if current_user.admin:
            return redirect(url_for('oee_displaying.machine_graph'))
        else:
            return redirect(url_for('oee_monitoring.production'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
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
                next_page = url_for('oee_displaying.machine_graph')
            else:
                next_page = url_for('oee_monitoring.production')
        return redirect(next_page)
    nav_bar_title = "Login"
    return render_template('login/login.html', title='Sign in', form=form, nav_bar_title=nav_bar_title)

    #todo When logging in and logging out, set the machine accordingly


@bp.route('/logout')
@login_required
def logout():
    """ Logs the user out of the system. """
    current_app.logger.info(f"Logging out {current_user}")
    logout_user()
    return redirect(url_for('login.login'))






