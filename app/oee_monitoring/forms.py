from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, IntegerField, widgets
from wtforms.fields.html5 import TelField


class StartForm(FlaskForm):
    machine_choices = []
    job_number = StringField('Job Number')
    machine = SelectField('Machine', choices=machine_choices)
    planned_set_time = IntegerField('Planned Set Time', widget=widgets.Input(input_type="number"))
    planned_cycle_time = IntegerField('Planned Cycle Time', widget=widgets.Input(input_type="number"))
    planned_cycle_quantity = IntegerField('Planned Cycle Quantity', widget=widgets.Input(input_type="number"))
    submit = SubmitField('Start')


class EndForm(FlaskForm):
    submit = SubmitField('End Job')
