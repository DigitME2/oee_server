from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, FloatField, HiddenField, TimeField, DateField, SelectField
from wtforms.validators import DataRequired

from app.visualisation.forms import TIME_FORMAT


class StartJobForm(FlaskForm):
    job_number = StringField('Job Number', validators=[DataRequired()])
    ideal_cycle_time = FloatField('Ideal Cycle Time (s)')

    submit = SubmitField('Set')


class EndJobForm(FlaskForm):
    quantity_good = IntegerField("Good Quantity")
    rejects = IntegerField("Rejects")
    submit = SubmitField("End")


class EditActivityForm(FlaskForm):
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT)
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT)
    submit = SubmitField('Submit')
    activity_code = SelectField()
    notes = StringField()
