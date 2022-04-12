from datetime import datetime, time

from flask import render_template, url_for, redirect, request, abort, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from wtforms.validators import NoneOf, DataRequired

from app.admin import bp
from app.admin.forms import ChangePasswordForm, ActivityCodeForm, RegisterForm, MachineForm, SettingsForm, \
    ScheduleForm, MachineGroupForm
from app.admin.helpers import admin_required, fix_colour_code
from app.default.models import Machine, MachineGroup, Activity, ActivityCode, Job, Settings, Schedule
from app.default.models import SHIFT_STRFTIME_FORMAT
from app.extensions import db
from app.login.models import User
from config import Config


@bp.route('/adminhome', methods=['GET'])
@login_required
@admin_required
def admin_home():
    """ The default page for a logged-in user"""
    # Create default database entries
    return render_template('admin/adminhome.html',
                           users=User.query.all(),
                           schedules=Schedule.query.all(),
                           machines=Machine.query.all(),
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
        db.session.add(current_settings)
        db.session.commit()
        current_app.logger.info(f"Changed settings: {current_settings}")
        return redirect(url_for('admin.admin_home'))

    # Set the form data to show the existing settings
    form.dashboard_update_interval.data = current_settings.dashboard_update_interval_s
    form.job_number_input_type.data = current_settings.job_number_input_type
    form.allow_delayed_job_start.data = current_settings.allow_delayed_job_start
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
    return render_template("admin/changepassword.html",
                           nav_bar_title=nav_bar_title,
                           user=user,
                           form=form)


@bp.route('/schedule', methods=['GET', 'POST'])
@login_required
@admin_required
def machine_schedule():
    form = ScheduleForm()

    schedule_id = request.args.get("schedule_id", None)

    if schedule_id is None or 'new' in request.args and request.args['new'] == "True":
        # Create a new schedule
        schedule = Schedule(name="")
        db.session.add(schedule)
    else:
        schedule = Schedule.query.get_or_404(schedule_id)

    if form.validate_on_submit():
        # Save the data from the form to the database
        schedule.name = form.name.data
        for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
            start = getattr(form, day + "_start").data.strftime(SHIFT_STRFTIME_FORMAT)
            end = getattr(form, day + "_end").data.strftime(SHIFT_STRFTIME_FORMAT)
            if end < start:
                db.session.rollback()
                return abort(400)
            setattr(schedule, day + "_start", start)
            setattr(schedule, day + "_end", end)
        db.session.commit()
        return redirect(url_for('admin.admin_home'))

    # Set the form data to show data from the database
    form.name.data = schedule.name
    blank_time = time().strftime(SHIFT_STRFTIME_FORMAT)  # Replace empty times with 00:00
    for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        start_form = getattr(form, day + "_start")
        start_form.data = datetime.strptime(getattr(schedule, day + "_start", blank_time) or blank_time,
                                            SHIFT_STRFTIME_FORMAT)
        end_form = getattr(form, day + "_end")
        end_form.data = datetime.strptime(getattr(schedule, day + "_end", blank_time) or blank_time,
                                          SHIFT_STRFTIME_FORMAT)
    return render_template("admin/schedule.html",
                           form=form)


@bp.route('/editmachine', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_machine():
    """The page to edit a machine (also used for creating a new machine)
    This page will allow an ID to be specified for new machines being created, but will not allow the ID
    to be changed for existing machines."""
    form = MachineForm()

    # Get a list of schedules to create form dropdown
    schedules = []
    for s in Schedule.query.all():
        schedules.append((str(s.id), str(s.name)))  # The ID has to be a string to match the data returned from client
    # Add the list of schedules to the form
    form.schedule.choices = schedules

    # Create machine group dropdown
    groups = [("0", str("No group"))]
    for g in MachineGroup.query.all():
        groups.append((str(g.id), str(g.name)))
    form.group.choices = groups

    form.workflow_type.choices = Config.WORKFLOW_TYPES

    # If new=true then the request is for a new machine to be created
    if 'new' in request.args and request.args['new'] == "True":
        creating_new_machine = True
    else:
        creating_new_machine = False

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

    # Get downtime codes for checkboxes
    always_excluded_downtime_codes = [Config.NO_USER_CODE_ID, Config.UPTIME_CODE_ID, Config.UNEXPLAINED_DOWNTIME_CODE_ID]
    activity_codes = ActivityCode.query.filter(ActivityCode.id.not_in(always_excluded_downtime_codes)).all()

    # Create validators for the form
    # Create a list of existing names and IPs to prevent duplicates being entered
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
    # Don't allow duplicate machine names
    form.name.validators = [NoneOf(names, message="Name already exists"), DataRequired()]
    # Don't allow duplicate device IPs
    form.device_ip.validators = [NoneOf(ips, message="This device is already assigned to a machine")]

    if form.validate_on_submit():
        current_app.logger.info(f"{machine} edited by {current_user}")
        # Save the new values on submit
        machine.name = form.name.data
        machine.active = form.active.data
        machine.workflow_type = form.workflow_type.data
        machine.job_start_input_type = form.job_start_input_type.data
        machine.autofill_job_start_input = form.autofill_input_bool.data
        machine.autofill_job_start_amount = form.autofill_input_amount.data
        machine.schedule_id = form.schedule.data

        # Process the checkboxes outside wtforms because it doesn't like lists of boolean fields for some reason
        for ac in activity_codes:
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
        # Save empty ip values as null to avoid unique constraint errors in the database
        if form.device_ip.data == "":
            machine.device_ip = None
        else:
            machine.device_ip = form.device_ip.data
        try:
            db.session.add(machine)
            db.session.commit()

        except IntegrityError as e:
            return str(e)
        # If creating a new machine, save the ID and start an activity on the machine
        if creating_new_machine:
            current_app.logger.info(f"{machine} created by {current_user}")
            first_act = Activity(time_start=datetime.now(),
                                 machine_state=Config.MACHINE_STATE_OFF,
                                 activity_code_id=Config.NO_USER_CODE_ID)
            db.session.add(first_act)
            current_app.logger.debug(f"{first_act} started on machine creation")
        return redirect(url_for('admin.admin_home'))

    # Fill out the form with existing values to display on the page
    form.active.data = machine.active
    form.schedule.data = str(machine.schedule_id)
    form.group.data = str(machine.group_id)
    form.workflow_type.data = str(machine.workflow_type)
    form.job_start_input_type.data = str(machine.job_start_input_type)
    form.autofill_input_bool.data = bool(machine.autofill_job_start_input)
    form.autofill_input_amount.data = machine.autofill_job_start_amount

    if not creating_new_machine:
        form.name.data = machine.name
        form.device_ip.data = machine.device_ip

    return render_template("admin/edit_machine.html",
                           form=form,
                           excluded_activity_code_ids=[code.id for code in machine.excluded_activity_codes],
                           activity_codes=activity_codes)


@bp.route('/editmachinegroup', methods=['GET', 'POST'])
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


@bp.route('/editactivitycode', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_activity_code():
    """The page to edit an activity code"""

    # If new=true then the request is for a new activity code to be created
    if 'new' in request.args and request.args['new'] == "True":
        # Create a new activity code
        activity_code = ActivityCode(active=True)
        message = "Create new activity code"

    # Otherwise, get the activity code to be edited
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
        activity_code.graph_colour = fix_colour_code(form.graph_colour.data)
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
