from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired, NoneOf, AnyOf


class StartForm(FlaskForm):

    # def __init__(self, *args, **kwargs):
    #     super(StartForm, self).__init__(*args, **kwargs)
    #     # Don't allow repeat job numbers
    #     if 'job_numbers' in kwargs:
    #         self.job_number.validators.append(NoneOf(kwargs['job_numbers']))
    #     self.job_number.validators.append(DataRequired())
    #
    #     # Load the choices for the machine numbers
    #     if 'machine_numbers' in kwargs:
    #         self.machine_number.choices = kwargs['machine_numbers']

    job_number = StringField('Job Number')
    machine_number = SelectField('Machine Number')
    submit = SubmitField('Start')


class EndForm(FlaskForm):
    submit = SubmitField('Finish')


class CompleteJobForm(FlaskForm):
    submit = SubmitField('Complete Job')