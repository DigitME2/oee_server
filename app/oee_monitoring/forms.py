from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired, NoneOf


class StartForm(FlaskForm):

    machine_choices = []
    job_number = StringField('Job Number')
    machine_number = SelectField('Machine Number', choices=machine_choices)
    submit = SubmitField('Start')


class EndForm(FlaskForm):
    submit = SubmitField('Finish')


class CompleteJobForm(FlaskForm):
    error_code = SelectField('Error Code', choices=[("1", "1"), ("2", "2")])
    submit = SubmitField('Complete Job')