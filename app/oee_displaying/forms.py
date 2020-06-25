import datetime
from flask_wtf import FlaskForm
from wtforms import DateField, PasswordField, StringField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, EqualTo, IPAddress, Optional, NoneOf, ValidationError
from wtforms.widgets import TextArea
from wtforms_components import TimeField

DATE_FORMAT = "%d-%m-%Y"
TIME_FORMAT = "%H:%M"
midnight = datetime.time(hour=0, minute=0, second=0,  microsecond=0)
MACHINES_CHOICES_HEADERS = ["--Groups--", "--Machines--"]

# Types of graphs that will be shown as options
state_gantt_chart = "State Gantt chart"
oee_line_graph = "OEE line graph"
downtime_bar_chart = "Downtime reasons bar chart"
job_table = "Job table"
GRAPH_TYPES = [oee_line_graph, state_gantt_chart, downtime_bar_chart, job_table]



class GanttForm(FlaskForm):
    form_template = "key_date_time"
    graph_name = "Machine Status Gantt Chart"
    description = "A Gantt chart showing the activity of a single machine or multiple machines. Time is plotted on the x-axis and different " \
                  "colours represent different activities."
    key = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")], id="gantt_machines")
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, label="Start Date (DD-MM-YYYY)")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, label="End Date (DD-MM-YYYY)")
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="gantt_start_time")
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="gantt_end_time")

    submit = SubmitField('Submit', id="gantt_submit")



class OeeLineForm(FlaskForm):
    form_template = "date"
    graph_name = "Machine group OEE Line Graph"
    description = "A line graph showing the daily OEE figure of every machine group between two dates"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="oee_line_start_date", label="Start Date (DD-MM-YYYY)")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="oee_line_end_date", label="End Date (DD-MM-YYYY)")

    submit = SubmitField('Submit', id="oee_line_submit")


class DowntimeBarForm(FlaskForm):
    form_template = "key_date_time"
    graph_name = "Downtime Bar Chart"
    description = "A bar chart showing the total amount of each activity for selected machines between two times"
    key = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")], id="downtime_bar_machines")
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="downtime_bar_start_date", label="Start Date (DD-MM-YYYY)")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="downtime_bar_end_date", label="End Date (DD-MM-YYYY)")
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="downtime_bar_start_time")
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="downtime_bar_end_time")

    submit = SubmitField('Submit', id="downtime_bar_submit")


class JobTableForm(FlaskForm):
    form_template = "date"
    graph_name = "Job Table"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="job_table_start_date", label="Start Date (DD-MM-YYYY)")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="job_table_end_date", label="End Date (DD-MM-YYYY)")

    submit = SubmitField('Submit', id="job_table_submit")


class WOTableForm(FlaskForm):
    form_template = "date"
    graph_name = "Work Order Table"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="wo_table_start_date", label="Start Date (DD-MM-YYYY)")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="wo_table_end_date", label="End Date (DD-MM-YYYY)")

    submit = SubmitField('Submit', id="wo_table_submit")


class ActivityDurationsTableForm(FlaskForm):
    form_template = "key_date_time"
    graph_name = "Activity Durations Table"
    key = SelectField(validators=[DataRequired()], choices=[("users", "Users"), ("machines", "Machines")])
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="activity_table_start_time")
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="activity_table_end_time")
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="activity_table_start_date", label="Start Date (DD-MM-YYYY)")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="activity_table_end_date", label="End Date (DD-MM-YYYY)")

    submit = SubmitField('Submit', id="activity_table_submit")


class RawDatabaseTableForm(FlaskForm):
    form_template = "key"
    graph_name = "Raw Database Table"
    key = SelectField(label="Table name", validators=[DataRequired()], choices=[("users", "Users"), ("machines", "Machines")])

    submit = SubmitField('Submit', id="raw_database_table_submit")