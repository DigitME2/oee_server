from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired, EqualTo, Email


class StartForm(FlaskForm):
    job_no = StringField('Job Number', validators=[DataRequired()])
    machine_number = StringField('Machine', validators=[DataRequired()])
    submit = SubmitField('Start')
