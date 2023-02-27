from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField, IntegerField, SelectField, RadioField, \
    FieldList, FloatField, TimeField
from wtforms.validators import DataRequired, EqualTo, Optional
from wtforms.widgets import TextArea

from config import Config

MACHINE_STATE_CHOICES = [(Config.MACHINE_STATE_UPTIME, "Uptime"),
                         (Config.MACHINE_STATE_UNPLANNED_DOWNTIME, "Unplanned downtime"),
                         (Config.MACHINE_STATE_PLANNED_DOWNTIME, "Planned downtime"),
                         (Config.MACHINE_STATE_OVERTIME, "Overtime")]


class ChangePasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(),
                                                         EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm New Password')
    submit = SubmitField('Change')


class ActivityCodeForm(FlaskForm):
    active = BooleanField()
    short_description = StringField(validators=[DataRequired()])
    long_description = StringField(widget=TextArea())
    machine_state = SelectField(choices=MACHINE_STATE_CHOICES, default=Config.MACHINE_STATE_UNPLANNED_DOWNTIME)
    downtime_category = SelectField(choices=Config.DOWNTIME_CATEGORIES)
    graph_colour = StringField(label="Colour", validators=[DataRequired()])
    submit = SubmitField('Save')


class ShiftForm(FlaskForm):
    name = StringField(label="Shift Name", validators=[DataRequired()])
    mon_start = TimeField(validators=[Optional()])
    mon_end = TimeField(validators=[Optional()])
    mon_disable = BooleanField(label="No Shifts")
    tue_start = TimeField(validators=[Optional()])
    tue_end = TimeField(validators=[Optional()])
    tue_disable = BooleanField(label="No Shifts")
    wed_start = TimeField(validators=[Optional()])
    wed_end = TimeField(validators=[Optional()])
    wed_disable = BooleanField(label="No Shifts")
    thu_start = TimeField(validators=[Optional()])
    thu_end = TimeField(validators=[Optional()])
    thu_disable = BooleanField(label="No Shifts")
    fri_start = TimeField(validators=[Optional()])
    fri_end = TimeField(validators=[Optional()])
    fri_disable = BooleanField(label="No Shifts")
    sat_start = TimeField(validators=[Optional()])
    sat_end = TimeField(validators=[Optional()])
    sat_disable = BooleanField(label="No Shifts")
    sun_start = TimeField(validators=[Optional()])
    sun_end = TimeField(validators=[Optional()])
    sun_disable = BooleanField(label="No Shifts")
    submit = SubmitField('Save')

    def validate_disabled_days(self):
        """ Don't allow time fields to be empty, except for the days that are disabled"""
        valid = True
        for day in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
            disable_day_input = getattr(self, day + "_disable")
            if disable_day_input.data:
                continue
            start_time = getattr(self, day + "_start")
            end_time = getattr(self, day + "_end")
            if not start_time.data:
                start_time.errors = ["Not a valid value"]
                valid = False
            if not end_time.data:
                end_time.errors = ["Not a valid value"]
                valid = False
        return valid


class MachineForm(FlaskForm):
    job_start_input_type_choices = [("cycle_time_seconds", "Ideal cycle time (seconds)"),
                                    ("cycle_time_minutes", "Ideal cycle time (minutes)"),
                                    ("cycle_time_hours", "Ideal cycle time (hours)"),
                                    ("parts_per_second", "Parts per second"),
                                    ("parts_per_minute", "Parts per minute"),
                                    ("parts_per_hour", "Parts per hour"),
                                    ("planned_qty_minutes", "Planned quantity & Planned time (minutes)"),
                                    ("no_cycle_time", "No Cycle Time Input")]

    active = BooleanField()
    name = StringField(validators=[DataRequired()])
    group = SelectField("Machine Group")
    workflow_type = SelectField("Workflow Type")
    shift_pattern = SelectField("Shift Pattern")
    end_job_on_shift_end = BooleanField("Stop active jobs when shift ends")
    job_start_input_type = SelectField("Cycle Time Input Type", choices=job_start_input_type_choices)
    autofill_input_bool = BooleanField("Enable Autofill", validators=[Optional()])
    autofill_input_amount = FloatField("Cycle Time Input Autofill")
    activity_codes_checkboxes = FieldList(BooleanField())
    job_start_activity = SelectField("First Activity on Job Start")
    job_number_input_type = RadioField("Job Code Input type", choices=[("text", "Alphanumeric"),
                                                                       ("number", "Numbers only")])
    submit = SubmitField('Save')


class MachineGroupForm(FlaskForm):
    id = IntegerField()
    name = StringField(validators=[DataRequired()])

    submit = SubmitField('Save')


class InputDeviceForm(FlaskForm):
    name = StringField("Name")
    machine = SelectField("Assigned Machine")

    submit = SubmitField('Save')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(),
                                                     EqualTo('confirm_password', message="Passwords do not match")])
    confirm_password = PasswordField('Confirm Password')
    submit = SubmitField('Register')
