from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo
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
    id = StringField()
    name = StringField(validators=[DataRequired()])
    submit = SubmitField('Save')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm Password')
    submit = SubmitField('Register')
