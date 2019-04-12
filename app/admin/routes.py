from flask import render_template, url_for, redirect, request, abort
from flask_login import login_required, current_user
from wtforms.validators import NoneOf, DataRequired

from app import db
from app.admin import bp
from app.admin.helpers import admin_required
from app.admin.forms import ChangePasswordForm, ActivityCodeForm, RegisterForm, MachineForm, SettingsForm
from app.default.models import Machine, ActivityCode, Job, UNEXPLAINED_DOWNTIME_CODE_ID, UPTIME_CODE_ID, Settings
from app.login.models import User


@bp.route('/adminhome', methods=['GET'])
@login_required
@admin_required
def admin_home():
    """ The default page for a logged-in user"""
    # Create default database entries
    return render_template('admin/adminhome.html',
                           machines=Machine.query.all(),
                           users=User.query.all(),
                           activity_codes=ActivityCode.query.all(),
                           jobs=Job.query.all())


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    current_settings = Settings.query.get_or_404(1)
    form = SettingsForm()
    if form.validate_on_submit():
        current_settings.threshold = form.explanation_threshold.data
        db.session.add(current_settings)
        db.session.commit()
        return redirect(url_for('admin.admin_home'))
    form.explanation_threshold.data = current_settings.threshold
    return render_template('admin/settings.html',
                           form=form)


@bp.route('/newuser', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """ The screen to register a new user."""

    form = RegisterForm()
    if form.validate_on_submit():
        # noinspection PyArgumentList
        u = User(username=form.username.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        return redirect(url_for('admin.admin_home'))
    nav_bar_title = "New User"
    return render_template("admin/newuser.html", title="Register", nav_bar_title=nav_bar_title, form=form)


@bp.route('/changepassword', methods=['GET', 'POST'])
@login_required
@admin_required
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
        return redirect(url_for('admin.admin_home'))
    nav_bar_title = "Change password for " + str(user.username)
    return render_template("admin/changepassword.html", nav_bar_title=nav_bar_title, user=user, form=form)


@bp.route('/editactivitycode', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_activity_code():
    """The page to edit an activity code"""

    # If new=true then the request is for a new activity code to be created
    if 'new' in request.args and request.args['new'] == "true":
        # Create a new activity code
        activity_code = ActivityCode(active=True)
        message = "Create new activity code"

    # Otherwise get the activity code to be edited
    elif 'ac_id' in request.args:
        try:
            activity_code_id = int(request.args['ac_id'])
            activity_code = ActivityCode.query.get_or_404(activity_code_id)
        except ValueError:
            error_message = "Error parsing ac_id : {code_id}".format(code_id=request.args['ac_id'])
            return abort(400, error_message)
        # Show a warning to the user depending on the code being edited.
        if activity_code_id == UPTIME_CODE_ID:
            message = "Warning: This code should always represent uptime"
        elif activity_code_id == UNEXPLAINED_DOWNTIME_CODE_ID:
            message = "Warning: This code should alway represent unexplained downtime"
        else:
            message = "Warning: Changes to these values will" \
                      " retroactively affect past readings with this activity code.<br> \
                      If this code is no longer needed, deselect \"In Active\" for this code " \
                      "and create another activity code."
    else:
        error_message = "No activity code specified"
        return abort(400, error_message)

    form = ActivityCodeForm()
    if form.validate_on_submit():
        activity_code.code = form.code.data
        activity_code.active = form.active.data
        activity_code.short_description = form.short_description.data
        activity_code.long_description = form.long_description.data
        activity_code.graph_colour = '#' + form.graph_colour.data
        db.session.add(activity_code)
        db.session.commit()
        return redirect(url_for('admin.admin_home'))

    # Fill out the form with existing values
    form.active.data = activity_code.active
    form.code.data = activity_code.code
    form.short_description.data = activity_code.short_description
    form.long_description.data = activity_code.long_description
    form.graph_colour.data = activity_code.graph_colour

    # Prevent duplicate codes from being created
    codes = []
    for ac in ActivityCode.query.all():
        codes.append(str(ac.code))
    if activity_code.code in codes:
        codes.remove(activity_code.code)
    form.code.validators = [NoneOf(codes), DataRequired()]

    return render_template("admin/edit_activity_code.html",
                           form=form,
                           message=message)


@bp.route('/editmachine', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_machine():
    """The page to edit an activity code"""

    # If new=true then the request is for a new activity code to be created
    if 'new' in request.args and request.args['new'] == "true":
        # Create a new activity code
        machine = Machine(name="")
        # Add and flush now to retrieve an id for the new entry
        db.session.add(machine)
        db.session.flush()
        message = "Create new machine"

    # Otherwise get the activity code to be edited
    elif 'machine_id' in request.args:
        try:
            machine_id = int(request.args['machine_id'])
            machine = Machine.query.get_or_404(machine_id)
        except ValueError:
            error_message = "Error parsing machine_id : {machine_id}".format(machine_id=request.args['machine_id'])
            return abort(400, error_message)
        # Show a warning to the user
        message = "Warning: This machine (ID {machine_id}) retains a reference to all of its past activity. " \
                  "It's recommended not to change which machine this ID refers to." \
                  "If the machine is no longer needed, deselect \"Active\" for this machine to hide it from the users."\
            .format(machine_id=machine_id)
    else:
        error_message = "No machine_id specified"
        return abort(400, error_message)

    form = MachineForm()
    if form.validate_on_submit():
        # Save the new values on submit
        machine.name = form.name.data
        machine.active = form.active.data
        db.session.add(machine)
        db.session.commit()
        return redirect(url_for('admin.admin_home'))

    # Fill out the form with existing values
    form.id.data = machine.id
    form.name.data = machine.name
    form.active.data = machine.active

    # Prevent duplicate machine names from being created
    names = []
    for m in Machine.query.all():
        names.append(str(m.name))
    # Don't prevent saving it with the same name
    if machine.name in names:
        names.remove(machine.name)
    form.name.validators = [NoneOf(names), DataRequired()]

    return render_template("admin/edit_machine.html",
                           form=form,
                           message=message)

