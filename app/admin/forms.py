from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField, IntegerField
from wtforms.validators import DataRequired, EqualTo, IPAddress, Optional
from wtforms.widgets import TextArea


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


class MachineForm(FlaskForm):
    active = BooleanField()
    id = IntegerField()
    name = StringField(validators=[DataRequired()])
    group = StringField("Machine Group", validators=[DataRequired()])
    device_ip = StringField("Operator Device IP Address", validators=[Optional(), IPAddress(ipv4=True, ipv6=False)])
    shift_1_start = IntegerField(validators=[DataRequired()])
    shift_1_end = IntegerField(validators=[DataRequired()])
    shift_2_start = IntegerField(validators=[DataRequired()])
    shift_2_end = IntegerField(validators=[DataRequired()])
    shift_3_start = IntegerField(validators=[DataRequired()])
    shift_3_end = IntegerField(validators=[DataRequired()])
    submit = SubmitField('Save')
    # todo validate times


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm Password')
    submit = SubmitField('Register')


class SettingsForm(FlaskForm):
    explanation_threshold = IntegerField('Explanation Threshold (Seconds)', validators=[DataRequired()])
    submit = SubmitField('Save')
