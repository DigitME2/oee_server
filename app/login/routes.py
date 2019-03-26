from app import db
from app.login import bp
from app.login.forms import LoginForm, RegisterForm, ChangePasswordForm
from app.login.models import User, create_default_users
from flask import abort, render_template, request, flash, redirect, url_for
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
    if current_user.is_authenticated:
        return redirect(url_for('oee_monitoring.production'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for('login.login'))
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('oee_monitoring.production')
        return redirect(next_page)
    nav_bar_title = "Login"
    return render_template('login/login.html', title='Sign in', form=form, nav_bar_title=nav_bar_title)


@bp.route('/logout')
@login_required
def logout():
    """ Logs the user out of the system. """
    logout_user()
    return redirect(url_for('login.login'))


@bp.route('/newuser', methods=['GET', 'POST'])
def new_user():
    """ The screen to register a new user."""

    form = RegisterForm()
    if form.validate_on_submit():
        # noinspection PyArgumentList
        u = User(username=form.username.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
    nav_bar_title = "New User"
    return render_template("login/newuser.html", title="Register", nav_bar_title=nav_bar_title, form=form)


@bp.route('/changepassword', methods=['GET', 'POST'])
@login_required
def change_password():
    """ The page to change a user's password. The user_id is passed to this page."""
    if current_user.admin is not True:
        abort(403)
    user = User.query.get_or_404(request.args.get('user_id'))
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        redirect(url_for('default.admin_home'))
    nav_bar_title = "Change password for " + str(user.username)
    return render_template("login/changepassword.html", nav_bar_title=nav_bar_title, user=user, form=form)
