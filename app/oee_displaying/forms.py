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
    graph_name = "Machine Status Gantt Chart"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="gantt_start_date")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="gantt_end_date")
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="gantt_start_time")
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="gantt_end_time")
    machines = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")], id="gantt_machines")

    submit = SubmitField('Submit', id="gantt_submit")


class DashboardGanttForm(FlaskForm):
    graph_name = "Machine Status Gantt Chart (Dashboard view)"
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="dashboard_gantt_start_time")
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="dashboard_gantt_end_time")
    graph_type = SelectField(choices=[(v, v) for v in GRAPH_TYPES], id="dashboard_gantt_graph_type")
    machines = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")], id="dashboard_gantt_machines")

    submit = SubmitField('Submit', id="dashboard_gantt_submit")


class OeeLineForm(FlaskForm):
    graph_name = "OEE Line Graph"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="oee_line_start_date")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="oee_line_end_date")

    submit = SubmitField('Submit', id="oee_line_submit")


class DowntimeBarForm(FlaskForm):
    graph_name = "Downtime Bar Chart"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="downtime_bar_start_date")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="downtime_bar_end_date")
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="downtime_bar_start_time")
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="downtime_bar_end_time")
    machines = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")], id="downtime_bar_machines")
    dashboard = BooleanField(label="Create Dashboard View", id="downtime_bar_dashboard")

    submit = SubmitField('Submit', id="downtime_bar_submit")


class JobTableForm(FlaskForm):
    graph_name = "Job Table"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="job_table_start_date")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="job_table_end_date")

    submit = SubmitField('Submit', id="job_table_submit")


class WOTableForm(FlaskForm):
    graph_name = "Work Order Table"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="wo_table_start_date")
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT, id="wo_table_end_date")

    submit = SubmitField('Submit', id="wo_table_submit")