from datetime import datetime, time
import os

import pandas as pd
from flask import render_template, url_for, redirect, request, abort, current_app, send_file
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from wtforms.validators import NoneOf, DataRequired

from app import db
from app.admin import bp
from app.admin.forms import ChangePasswordForm, ActivityCodeForm, RegisterForm, MachineForm, SettingsForm
from app.admin.helpers import admin_required
from app.default.models import Machine, Activity, ActivityCode, Job, Settings, SHIFT_STRFTIME_FORMAT
from config import Config
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
    # Get the current settings. There can only be one row in the settings table.
    current_settings = Settings.query.get_or_404(1)
    form = SettingsForm()
    if form.validate_on_submit():
        # Save the new settings
        current_settings.dashboard_update_interval_s = form.dashboard_update_interval.data
        current_settings.threshold = form.explanation_threshold.data
        db.session.add(current_settings)
        db.session.commit()
        current_app.logger.info(f"Changed settings: {current_settings}")
        return redirect(url_for('admin.admin_home'))

    # Set the form data to show the existing settings
    form.dashboard_update_interval.data = current_settings.dashboard_update_interval_s
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
        current_app.logger.info(f"Created new user: {u}")
        return redirect(url_for('admin.admin_home'))
    nav_bar_title = "New User"
    return render_template("admin/newuser.html", title="Register",
                           nav_bar_title=nav_bar_title,
                           form=form)


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
        current_app.logger.info(f"Changed password for {user}")
        return redirect(url_for('admin.admin_home'))
    nav_bar_title = "Change password for " + str(user.username)
    return render_template("admin/changepassword.html",
                           nav_bar_title=nav_bar_title,
                           user=user,
                           form=form)


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
            error_message = f"Error parsing ac_id : {request.args['ac_id']} from URL"
            current_app.logger.warn(error_message)
            return abort(400, error_message)
        # Show a warning to the user depending on the code being edited.
        if activity_code_id == Config.UPTIME_CODE_ID:
            message = f"Warning: This entry (ID {activity_code_id}) should always represent uptime"
        elif activity_code_id == Config.UNEXPLAINED_DOWNTIME_CODE_ID:
            message = f"Warning: This entry (ID {activity_code_id}) should always represent unexplained downtime"
        elif activity_code_id == Config.SETTING_CODE_ID:
            message = f"Warning: This entry (ID {activity_code_id}) should always represent setting"
        else:
            message = "Warning: Changes to these values will be reflected in " \
                      "past readings with this activity code.<br> \
                      If this code is no longer needed, deselect \"Active\" for this code " \
                      "and create another activity code instead."
    else:
        error_message = "No activity code specified in URL"
        current_app.logger.warn(error_message)
        return abort(400, error_message)

    form = ActivityCodeForm()
    # Get a list of existing activity codes to use for form validation to prevent repeat codes
    all_activity_codes = []
    for ac in ActivityCode.query.all():
        all_activity_codes.append(str(ac.code))
    if activity_code.code in all_activity_codes:
        all_activity_codes.remove(activity_code.code)  # Don't prevent the form from entering the current code
    form.code.validators = [NoneOf(all_activity_codes, message="Code already exists"), DataRequired()]

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
    """The page to edit a machine (also used for creating a new machine)
    This page will allow an ID to be specified for new machines being created, but will not allow the ID
    to be changed for existing machines."""
    form = MachineForm()
    ids = []

    # If new=true then the request is for a new machine to be created
    if 'new' in request.args and request.args['new'] == "true":
        new_machine = True
    else:
        new_machine = False

    if new_machine:
        # Create a new machine
        machine = Machine(name="", active=True)
        # Add and flush now to retrieve an id for the new entry
        db.session.add(machine)
        db.session.flush()
        message = "Create new machine"

        # Create a list of existing machine IDs to pass to data validation
        for m in Machine.query.all():
            ids.append(m.id)
        # Allow it to accept the id that has just been assigned for the new entry
        if machine.id in ids:
            ids.remove(machine.id)

    # Otherwise get the machine to be edited
    elif 'machine_id' in request.args:
        # Prevent the ID from being edited for existing machines
        form.id.render_kw = {'readonly': True}
        try:
            machine_id = int(request.args['machine_id'])
            machine = Machine.query.get_or_404(machine_id)
        except ValueError:
            current_app.logger.warn(f"Error parsing machine_id in URL. "
                                    f"machine_id provided : {request.args['machine_id']}")
            error_message = f"Error parsing machine_id : {request.args['machine_id']}"
            return abort(400, error_message)
        # Show a warning to the user
        message = f"This machine ID ({machine_id}) can only be set when a new machine is being created. " \
                  "If the machine is no longer needed, deselect \"Active\" for this machine to hide it from the users."

    else:
        error_message = "No machine_id specified"
        current_app.logger.warn("No machine_id specified in URL")
        return abort(400, error_message)

    # Don't allow duplicate IDs
    form.id.validators = [NoneOf(ids, message="A machine with that ID already exists"), DataRequired()]

    # Create a list of existing names and IPs for validation
    names = []
    ips = []
    for m in Machine.query.all():
        names.append(str(m.name))
        ips.append(str(m.device_ip))
    # Don't prevent saving with its own current name/IP
    if machine.name in names:
        names.remove(machine.name)
    if machine.device_ip in ips:
        ips.remove(machine.device_ip)
    # Don't allow duplicate names
    form.name.validators = [NoneOf(names, message="Name already exists"), DataRequired()]
    # Don't allow duplicate IPs
    form.device_ip.validators = [NoneOf(ips, message="This device is already assigned to a machine"), DataRequired()]

    if form.validate_on_submit():
        current_app.logger.info(f"{machine} edited by {current_user}")
        # Save the new values on submit
        machine.name = form.name.data
        machine.active = form.active.data
        machine.group = form.group.data
        machine.schedule_start_1 = form.shift_1_start.data.strftime(SHIFT_STRFTIME_FORMAT)
        machine.schedule_end_1 = form.shift_1_end.data.strftime(SHIFT_STRFTIME_FORMAT)
        machine.schedule_start_2 = form.shift_2_start.data.strftime(SHIFT_STRFTIME_FORMAT)
        machine.schedule_end_2 = form.shift_2_end.data.strftime(SHIFT_STRFTIME_FORMAT)
        machine.schedule_start_3 = form.shift_3_start.data.strftime(SHIFT_STRFTIME_FORMAT)
        machine.schedule_end_3 = form.shift_3_end.data.strftime(SHIFT_STRFTIME_FORMAT)
        # Save empty ip values as null to avoid unique constraint errors in the database
        if form.device_ip.data == "":
            machine.device_ip = None
        else:
            machine.device_ip = form.device_ip.data

        # If creating a new machine, save the ID and start an activity on the machine
        if 'new' in request.args and request.args['new'] == "true":
            machine.id = form.id.data
            current_app.logger.info(f"{machine} created by {current_user}")
            first_act = Activity(machine_id=machine.id,
                                 timestamp_start=datetime.now().timestamp(),
                                 machine_state=Config.MACHINE_STATE_OFF,
                                 activity_code_id=Config.NO_USER_CODE_ID)
            db.session.add(first_act)
            current_app.logger.debug(f"{first_act} started on machine creation")

        try:
            db.session.add(machine)
            db.session.commit()

        except IntegrityError as e:
            return str(e)

        return redirect(url_for('admin.admin_home'))

    # Fill out the form with existing values to display on the page
    form.id.data = machine.id
    form.active.data = machine.active
    if not new_machine:
        form.name.data = machine.name
        form.group.data = machine.group
        form.device_ip.data = machine.device_ip
        form.shift_1_start.data = datetime.strptime(machine.schedule_start_1 or "", SHIFT_STRFTIME_FORMAT)
        form.shift_1_end.data = datetime.strptime(machine.schedule_end_1, SHIFT_STRFTIME_FORMAT)
        form.shift_2_start.data = datetime.strptime(machine.schedule_start_2, SHIFT_STRFTIME_FORMAT)
        form.shift_2_end.data = datetime.strptime(machine.schedule_end_2, SHIFT_STRFTIME_FORMAT)
        form.shift_3_start.data = datetime.strptime(machine.schedule_start_3, SHIFT_STRFTIME_FORMAT)
        form.shift_3_end.data = datetime.strptime(machine.schedule_end_3, SHIFT_STRFTIME_FORMAT)
    return render_template("admin/edit_machine.html",
                           form=form,
                           message=message)


@bp.route('/export', methods=['GET'])
def export():
    query = str(Job.query.filter_by(user_id=1).statement.compile(compile_kwargs={"literal_binds": True}))
    df = pd.read_sql(sql=query, con=db.engine)

    # Convert the times to a readable format
    df['start_time'] = list(map(datetime.fromtimestamp, df["start_time"]))
    df['end_time'] = list(map(datetime.fromtimestamp, df["end_time"]))

    filename = 'output.csv'
    directory = os.path.join('app', 'static', 'temp')
    if not os.path.exists(directory):
        os.mkdir(directory)
    filepath = os.path.abspath(os.path.join(directory, filename))
    # Delete the old temporary file
    if os.path.exists(filepath):
        os.remove(filepath)

    df.to_csv(filepath)
    new_file_name = "testy.csv"
    return send_file(filename_or_fp=filepath, cache_timeout=-1, as_attachment=True, attachment_filename=new_file_name)
