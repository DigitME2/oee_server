from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField, IntegerField, SelectField, RadioField, \
    FieldList, FloatField
from wtforms.validators import DataRequired, EqualTo, Optional
from wtforms.widgets import TextArea
from wtforms_components import TimeField


class ChangePasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(),
                                                         EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm New Password')
    submit = SubmitField('Change')


class ActivityCodeForm(FlaskForm):
    active = BooleanField()
    code = StringField()
    short_description = StringField(validators=[DataRequired()])
    long_description = StringField(widget=TextArea())
    graph_colour = StringField(validators=[DataRequired()])
    submit = SubmitField('Save')


class ScheduleForm(FlaskForm):
    error_message = "Enter 00:00 if no shift on this day"
    name = StringField(label="Schedule Name", validators=[DataRequired(message=error_message)])
    mon_start = TimeField(validators=[DataRequired(message=error_message)])
    mon_end = TimeField(validators=[DataRequired(message=error_message)])
    tue_start = TimeField(validators=[DataRequired(message=error_message)])
    tue_end = TimeField(validators=[DataRequired(message=error_message)])
    wed_start = TimeField(validators=[DataRequired(message=error_message)])
    wed_end = TimeField(validators=[DataRequired(message=error_message)])
    thu_start = TimeField(validators=[DataRequired(message=error_message)])
    thu_end = TimeField(validators=[DataRequired(message=error_message)])
    fri_start = TimeField(validators=[DataRequired(message=error_message)])
    fri_end = TimeField(validators=[DataRequired(message=error_message)])
    sat_start = TimeField(validators=[DataRequired(message=error_message)])
    sat_end = TimeField(validators=[DataRequired(message=error_message)])
    sun_start = TimeField(validators=[DataRequired(message=error_message)])
    sun_end = TimeField(validators=[DataRequired(message=error_message)])
    submit = SubmitField('Save')


class MachineForm(FlaskForm):
    job_start_input_type_choices = [("cycle_time_seconds", "Ideal cycle time (seconds)"),
                                    ("cycle_time_minutes", "Ideal cycle time (minutes)"),
                                    ("cycle_time_hours", "Ideal cycle time (hours)"),
                                    ("parts_per_second", "Parts per second"),
                                    ("parts_per_minute", "Parts per minute"),
                                    ("parts_per_hour", "Parts per hour"),
                                    ("planned_qty_minutes", "Planned quantity & Planned time (minutes)"),
                                    ("no_cycle_time", "No Cycle Time Input")]

    active = BooleanField()
    name = StringField(validators=[DataRequired()])
    group = SelectField("Machine Group")
    workflow_type = SelectField("Workflow Type")
    schedule = SelectField("Schedule")
    job_start_input_type = SelectField("Job Start Input Type", choices=job_start_input_type_choices)
    autofill_input_bool = BooleanField("Enable Autofill", validators=[Optional()])
    autofill_input_amount = FloatField("Job Start Input Autofill")
    activity_codes_checkboxes = FieldList(BooleanField())
    job_start_activity = SelectField("First Activity on Job Start")
    submit = SubmitField('Save')


class MachineGroupForm(FlaskForm):
    id = IntegerField()
    name = StringField(validators=[DataRequired()])

    submit = SubmitField('Save')


class InputDeviceForm(FlaskForm):
    name = StringField("Name")
    machine = SelectField("Assigned Machine")

    submit = SubmitField('Save')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm Password')
    submit = SubmitField('Register')


class SettingsForm(FlaskForm):
    dashboard_update_interval = IntegerField('Dashboard update frequency (Seconds)', validators=[DataRequired()])
    job_number_input_type = RadioField("Job Code Input type", choices=[("text", "Alphanumeric"),
                                                                       ("number", "Numbers only")])
    allow_delayed_job_start = BooleanField("Allow operator to enter adjusted start time during job start")
    allow_concurrent_user_jobs = BooleanField("Allow operators to have multiple active jobs/logons at once")
    submit = SubmitField('Save')
