from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, EqualTo, IPAddress, Optional
from wtforms.widgets import TextArea
from wtforms_components import TimeField


class ChangePasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm Password')
    submit = SubmitField('Change')


class ActivityCodeForm(FlaskForm):
    active = BooleanField()
    code = StringField(validators=[DataRequired()])
    short_description = StringField(validators=[DataRequired()])
    long_description = StringField(widget=TextArea())
    graph_colour = StringField(validators=[DataRequired()])
    submit = SubmitField('Save')


class ScheduleForm(FlaskForm):
    error_message = "Enter 00:00 if no shift on this day"
    name = StringField(validators=[DataRequired(message=error_message)])
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
    active = BooleanField()
    id = IntegerField()
    name = StringField(validators=[DataRequired()])
    group = StringField("Machine Group", validators=[DataRequired()])
    device_ip = StringField("Operator Device IP Address", validators=[Optional(), IPAddress(ipv4=True, ipv6=False)])
    workflow_type = SelectField("Workflow Type")
    schedule = SelectField("Schedule")
    submit = SubmitField('Save')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm Password')
    submit = SubmitField('Register')


class SettingsForm(FlaskForm):
    dashboard_update_interval = IntegerField('Dashboard update frequency (Seconds)', validators=[DataRequired()])
    explanation_threshold = IntegerField('Explanation Threshold (Seconds)', validators=[DataRequired()])
    submit = SubmitField('Save')
