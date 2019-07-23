from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField


class StartForm(FlaskForm):
    machine_choices = []
    job_number = StringField('Job Number')
    machine = SelectField('Machine', choices=machine_choices)
    planned_set_time = StringField('Planned Set Time')
    planned_cycle_time = StringField('Planned Cycle Time')
    planned_cycle_quantity = StringField('Planned Cycle Quantity')
    submit = SubmitField('Start')


class EndForm(FlaskForm):
    submit = SubmitField('End Job')


class CompleteJobForm(FlaskForm):
    error_code = SelectField('Error Code', choices=[("1", "1"), ("2", "2")])
    submit = SubmitField('Complete Job')
