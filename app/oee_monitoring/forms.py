from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField


class StartForm(FlaskForm):
    machine_choices = []
    job_number = StringField('Job Number')
    machine_number = SelectField('Machine Number', choices=machine_choices)
    submit = SubmitField('Start')


class EndForm(FlaskForm):
    submit = SubmitField('End Job')


class CompleteJobForm(FlaskForm):
    error_code = SelectField('Error Code', choices=[("1", "1"), ("2", "2")])
    submit = SubmitField('Complete Job')