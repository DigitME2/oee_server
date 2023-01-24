from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, FloatField, HiddenField, TimeField, DateField, SelectField
from wtforms.validators import DataRequired

from app.default.models import ActivityCode
from app.visualisation.forms import TIME_FORMAT


class BaseTimeAndDatesForm(FlaskForm):
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT)
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT)
    start_date = DateField(validators=[DataRequired()], label="Start Date")
    end_date = DateField(validators=[DataRequired()], label="End Date")
    submit = SubmitField('Submit')


class StartJobForm(FlaskForm):
    job_number = StringField('Job Number', validators=[DataRequired()])
    ideal_cycle_time = IntegerField('Ideal Cycle Time (s)')

    submit = SubmitField('Set')


class RecordProductionForm(FlaskForm):
    quantity_good = IntegerField("Good Quantity")
    quantity_rejects = IntegerField("Rejects Quantity")
    submit = SubmitField("End")


class FullJobForm(BaseTimeAndDatesForm):
    job_number = StringField('Job Number', validators=[DataRequired()])
    ideal_cycle_time = FloatField('Ideal Cycle Time (s)')
    quantity_good = IntegerField("Good Quantity")
    quantity_rejects = IntegerField("Rejects")

    submit = SubmitField("end")


class EditActivityForm(BaseTimeAndDatesForm):
    activity_code = SelectField()
    notes = StringField()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        activity_code_choices = []
        for ac in ActivityCode.query.all():
            activity_code_choices.append((str(ac.id), str(ac.short_description)))
        self.activity_code.choices = activity_code_choices


class ModifyProductionForm(BaseTimeAndDatesForm):
    quantity_good = IntegerField("Good Quantity")
    quantity_rejects = IntegerField("Rejects Quantity")


class RecordPastProductionForm(BaseTimeAndDatesForm):
    job = SelectField()
    quantity_good = IntegerField("Good Quantity")
    quantity_rejects = IntegerField("Rejects Quantity")
