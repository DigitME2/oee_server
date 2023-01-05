from datetime import datetime, time
from distutils.util import strtobool

from flask import render_template, url_for, redirect, request, abort, current_app, flash
from flask_login import login_required, current_user
from sqlalchemy import func
from wtforms.validators import NoneOf, DataRequired

from app.admin import bp
from app.admin.forms import ChangePasswordForm, ActivityCodeForm, RegisterForm, MachineForm, SettingsForm, \
    ShiftForm, MachineGroupForm, InputDeviceForm
from app.admin.helpers import admin_required, fix_colour_code, create_shift_day, load_shift_form_values, \
    ModifiedShiftException, save_shift_form
from app.default.helpers import DAYS

from app.default.helpers import get_current_machine_shift_period
from app.default.models import Machine, MachineGroup, Activity, ActivityCode, Job, Settings, InputDevice, ShiftPeriod, \
    Shift
from app.default.models import SHIFT_STRFTIME_FORMAT
from app.extensions import db
from app.login.models import User
from config import Config


@bp.route('/admin-home', methods=['GET'])
@login_required
@admin_required
def admin_home():
    """ The default page for a logged-in user"""
    # Create default database entries
    return render_template('admin/admin_home.html',
                           users=User.query.all(),
                           shifts=Shift.query.all(),
                           machines=Machine.query.all(),
                           input_devices=InputDevice.query.all(),
                           machine_groups=MachineGroup.query.all(),
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
        current_settings.job_number_input_type = form.job_number_input_type.data
        current_settings.allow_delayed_job_start = form.allow_delayed_job_start.data
        current_settings.allow_concurrent_user_jobs = form.allow_concurrent_user_jobs.data
        db.session.add(current_settings)
        db.session.commit()
        current_app.logger.info(f"Changed settings: {current_settings}")
        return redirect(url_for('admin.admin_home'))

    # Set the form data to show the existing settings
    form.dashboard_update_interval.data = current_settings.dashboard_update_interval_s
    form.job_number_input_type.data = current_settings.job_number_input_type
    form.allow_delayed_job_start.data = current_settings.allow_delayed_job_start
    form.allow_concurrent_user_jobs.data = current_settings.allow_concurrent_user_jobs
    return render_template('admin/settings.html',
                           form=form)


@bp.route('/new-user', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """ The screen to register a new user."""

    form = RegisterForm()
    # Get a list of existing users for form validation
    usernames = []
    for user in User.query.all():
        usernames.append(str(user.username))
    form.username.validators = [NoneOf(usernames, message="User already exists"), DataRequired()]

    if form.validate_on_submit():
        # noinspection PyArgumentList
        u = User(username=form.username.data)
        u.set_password(form.password.data)
        db.session.add(u)
        db.session.commit()
        current_app.logger.info(f"Created new user: {u}")
        return redirect(url_for('admin.admin_home'))
    nav_bar_title = "New User"
    return render_template("admin/new_user.html", title="Register",
                           nav_bar_title=nav_bar_title,
                           form=form)


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
@admin_required
def change_password():
    """ The page to change a user's password. The user_id is passed to this page."""
    if not current_app.config['LOGIN_DISABLED'] and not current_user.admin:
        return abort(403)
    user = User.query.get_or_404(request.args.get('user_id'))
    form = ChangePasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info(f"Changed password for {user}")
        return redirect(url_for('admin.admin_home'))
    nav_bar_title = "Change password for " + str(user.username)
    return render_template("admin/change_password.html",
                           nav_bar_title=nav_bar_title,
                           user=user,
                           form=form)


@bp.route('/edit-shift', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_shift():
    form = ShiftForm()

    shift_id = request.args.get("shift_id", None)

    if shift_id is None or 'new' in request.args and request.args['new'] == "True":
        new_shift = True
        # Create a new shift
        shift = Shift(name="")
        db.session.add(shift)
        db.session.flush()
        db.session.refresh(shift)
    else:
        new_shift = False
        shift = Shift.query.get_or_404(shift_id)

    if form.validate_on_submit() and form.validate_disabled_days():
        # Save the data from the form to the database
        save_shift_form(form, shift)
        return redirect(url_for('admin.admin_home'))

    if not new_shift:
        # Set the form data to show data from the database
        form.name.data = shift.name
        try:
            form = load_shift_form_values(form, shift)
        except ModifiedShiftException:
            flash(f"Shift pattern \"{shift.name}\" has been modified manually and cannot be edited here."
                  " Edit values directly in the database or create a new shift pattern.")
            return redirect(url_for('admin.admin_home'))
    return render_template("admin/shift.html",
                           form=form)


@bp.route('/input-device', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_input_device():
    input_device_id = request.args.get("id", None)
    input_device = InputDevice.query.get_or_404(input_device_id)

    form = InputDeviceForm()
    form.machine.choices = [("0", "Unassigned")] + [(str(m.id), str(m.name)) for m in Machine.query.all()]

    # Machine validator, prevent saving as a machine that is already assigned to another tablet (allow id=0)
    assigned_machines = [str(d.machine_id) for d in InputDevice.query.all()
                         if d.machine_id not in [input_device.machine_id, 0]]
    form.machine.validators = [NoneOf(assigned_machines, message="Machine already assigned to another device"),
                               DataRequired()]

    if form.validate_on_submit():
        # Save the data from the form to the database
        input_device.name = form.name.data

        if form.machine.data == "0":
            input_device.machine_id = None
        else:
            input_device.machine_id = form.machine.data
        db.session.commit()
        return redirect(url_for('admin.admin_home'))

    # Set the form data to show data from the database
    form.name.data = input_device.name
    form.machine.data = str(input_device.machine_id)

    return render_template("admin/edit_input_device.html",
                           form=form)


@bp.route('/edit-machine', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_machine():
    """The page to edit a machine (also used for creating a new machine)
    This page will allow an ID to be specified for new machines being created, but will not allow the ID
    to be changed for existing machines."""
    form = MachineForm()

    form.shift_pattern.choices = [(str(s.id), str(s.name)) for s in Shift.query.all()]

    # Create machine group dropdown
    groups = [("0", "No group")] + [(str(g.id), str(g.name)) for g in MachineGroup.query.all()]
    form.group.choices = groups

    form.workflow_type.choices = Config.WORKFLOW_TYPES

    # If new=true then the request is for a new machine to be created
    creating_new_machine = ('new' in request.args and strtobool(request.args['new']))

    if creating_new_machine:
        # Create a new machine
        machine = Machine(name="", active=True)

    # Otherwise, get the machine to be edited
    elif 'machine_id' in request.args:
        try:
            machine_id = int(request.args['machine_id'])
            machine = Machine.query.get_or_404(machine_id)
        except ValueError:
            current_app.logger.warn(f"Error parsing machine_id in URL. "
                                    f"machine_id provided : {request.args['machine_id']}")
            error_message = f"Error parsing machine_id : {request.args['machine_id']}"
            return abort(400, error_message)

    else:
        error_message = "No machine_id specified"
        current_app.logger.warn("No machine_id specified in URL")
        return abort(400, error_message)

    # Get downtime codes for exclusion checkboxes
    non_excludable_codes = [Config.UPTIME_CODE_ID, Config.UNEXPLAINED_DOWNTIME_CODE_ID]
    optional_activity_codes = ActivityCode.query.filter(ActivityCode.id.not_in(non_excludable_codes)).all()

    # Create first activity dropdown
    activity_code_choices = []
    for ac in ActivityCode.query.all():
        activity_code_choices.append((str(ac.id), str(ac.short_description)))
    form.group.choices = groups
    form.job_start_activity.choices = activity_code_choices

    # Create validators for the form
    # Create a list of existing names to prevent duplicates being entered
    names = []
    for m in Machine.query.all():
        names.append(str(m.name))
    # Don't prevent saving with its own current name
    if machine.name in names:
        names.remove(machine.name)
    # Don't allow duplicate machine names
    form.name.validators = [NoneOf(names, message="Name already exists"), DataRequired()]

    if form.validate_on_submit():
        current_app.logger.info(f"{machine} edited by {current_user}")
        # Save the new values on submit
        machine.name = form.name.data
        machine.active = form.active.data
        machine.workflow_type = form.workflow_type.data
        machine.job_start_input_type = form.job_start_input_type.data
        machine.autofill_job_start_input = form.autofill_input_bool.data
        machine.autofill_job_start_amount = form.autofill_input_amount.data
        machine.shift_id = form.shift_pattern.data
        machine.job_start_activity_id = form.job_start_activity.data

        # Process the checkboxes outside wtforms because it doesn't like lists of boolean fields for some reason
        for ac in optional_activity_codes:
            if ac.short_description not in request.form and ac not in machine.excluded_activity_codes:
                # If it's not checked, and it's not in the excluded activity codes, add it
                machine.excluded_activity_codes.append(ac)
            if ac.short_description in request.form and ac in machine.excluded_activity_codes:
                # If it's checked, and it's already in the excluded activity codes, remove it
                machine.excluded_activity_codes.pop(machine.excluded_activity_codes.index(ac))

        # If no machine group is selected, null the column instead of 0
        if form.group.data == '0':
            machine.group_id = None
        else:
            machine.group_id = form.group.data

        # If creating a new machine, save the ID and start an activity on the machine
        if creating_new_machine:
            machine.current_activity_id = -1  # Temporary to prevent integrity while we create the activity
            db.session.add(machine)
            db.session.flush()
            db.session.refresh(machine)
            current_app.logger.info(f"{machine} created by {current_user}")
            first_act = Activity(start_time=datetime.now(),
                                 machine_id=machine.id,
                                 machine_state=Config.MACHINE_STATE_UNPLANNED_DOWNTIME,
                                 activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID)
            db.session.add(first_act)
            db.session.flush()
            db.session.refresh(first_act)
            machine.current_activity_id = first_act.id
            current_app.logger.debug(f"{first_act} started on machine creation")

        # Set current machine state according to current shift
        current_shift_period = get_current_machine_shift_period(machine)
        machine.schedule_state = current_shift_period.shift_state
        db.session.commit()
        return redirect(url_for('admin.admin_home'))

    # Fill out the form with existing values to display on the page
    form.active.data = machine.active
    form.shift_pattern.data = str(machine.shift_id)
    form.group.data = str(machine.group_id)
    form.workflow_type.data = str(machine.workflow_type)
    form.job_start_input_type.data = str(machine.job_start_input_type)
    form.autofill_input_bool.data = bool(machine.autofill_job_start_input)
    form.autofill_input_amount.data = machine.autofill_job_start_amount
    form.job_start_activity.data = str(machine.job_start_activity_id)

    if not creating_new_machine:
        form.name.data = machine.name

    return render_template("admin/edit_machine.html",
                           form=form,
                           excluded_activity_code_ids=[code.id for code in machine.excluded_activity_codes],
                           activity_codes=optional_activity_codes)


@bp.route('/edit-machine-group', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_machine_group():
    """The page to edit a machine (also used for creating a new machine)
    This page will allow an ID to be specified for new machines being created, but will not allow the ID
    to be changed for existing machines."""
    form = MachineGroupForm()
    all_machine_groups = MachineGroup.query.all()

    # If new=true then the request is for a new machine group to be created
    if 'new' in request.args and request.args['new'] == "True":
        creating_new_group = True
    else:
        creating_new_group = False

    if creating_new_group:
        # Create a new machine
        machine_group = MachineGroup(name="")
        db.session.add(machine_group)

    # Otherwise, get the machine group to be edited
    elif 'machine_group_id' in request.args:
        try:
            machine_group_id = int(request.args['machine_group_id'])
            machine_group = MachineGroup.query.get_or_404(machine_group_id)
        except ValueError:
            current_app.logger.warn(f"Error parsing machine_group_id in URL. "
                                    f"machine_group_id provided : {request.args['machine_group_id']}")
            error_message = f"Error parsing machine_group_id : {request.args['machine_group_id']}"
            return abort(400, error_message)

    else:
        error_message = "No machine_group_id specified"
        current_app.logger.warn("No machine_group_id specified in URL")
        return abort(400, error_message)

    # Create validators for the form
    # Create a list of existing names to prevent duplicates being entered
    names = []
    for mg in all_machine_groups:
        names.append(str(mg.name))
    # Don't prevent saving with its own current name
    if machine_group.name in names:
        names.remove(machine_group.name)

    # Don't allow duplicate machine names
    form.name.validators = [NoneOf(names, message="Name already exists"), DataRequired()]

    if form.validate_on_submit():
        current_app.logger.info(f"{machine_group} edited by {current_user}")
        # Save the new values on submit
        machine_group.name = form.name.data
        db.session.commit()

        return redirect(url_for('admin.admin_home'))

    # Fill out the form with existing values to display on the page
    if not creating_new_group:
        form.name.data = machine_group.name

    return render_template("admin/edit_machine_group.html",
                           form=form,
                           group_machines=machine_group.machines)


@bp.route('/edit-activity-code', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_activity_code():
    """The page to edit an activity code"""
    # TODO Create hard-coded categories to help with data analysis
    # Get the activity code to be edited (If no code is given we will create a new one)
    if 'ac_id' in request.args:
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
        else:
            message = "Changes to these values will be reflected in " \
                      "past readings with this activity code.<br> \
                      If this code is no longer needed, deselect \"Active\" for this code " \
                      "and create another activity code instead."
    else:
        activity_code = None
        message = "Create new activity code"

    form = ActivityCodeForm()
    # Get a list of existing activity codes to use for form validation to prevent repeat codes
    short_descriptions = []
    for ac in ActivityCode.query.all():
        short_descriptions.append(str(ac.short_description))
    if activity_code:
        # Don't prevent the form from entering the current code
        short_descriptions.remove(activity_code.short_description)
    form.short_description.validators = [NoneOf(short_descriptions, message="Code already exists"), DataRequired()]
    if form.validate_on_submit():
        if not activity_code:  # Create a new activity code
            # Set the ID manually (instead of autoincrement) due to issues with Postgresql
            # These issues occur because we manually assigned the IDs of the first 3 activity codes
            activity_code_id = db.session.query(func.max(ActivityCode.id)).first()[0] + 1
            activity_code = ActivityCode(id=activity_code_id, active=True)
        activity_code.code = form.code.data
        activity_code.active = form.active.data
        activity_code.short_description = form.short_description.data
        activity_code.long_description = form.long_description.data
        activity_code.graph_colour = fix_colour_code(form.graph_colour.data)
        db.session.add(activity_code)
        db.session.commit()
        return redirect(url_for('admin.admin_home'))

    form.active.data = True
    if activity_code:
        # Fill out the form with existing values
        form.active.data = activity_code.active
        form.code.data = activity_code.code
        form.short_description.data = activity_code.short_description
        form.long_description.data = activity_code.long_description
        form.graph_colour.data = activity_code.graph_colour

    return render_template("admin/edit_activity_code.html",
                           form=form,
                           message=message)
