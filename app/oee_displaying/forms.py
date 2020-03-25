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
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT)
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT)
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight)
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight)
    machines = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")])

    submit = SubmitField('Submit')


class DashboardGanttForm(FlaskForm):
    graph_name = "Machine Status Gantt Chart (Dashboard view)"
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight)
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight)
    graph_type = SelectField(choices=[(v, v) for v in GRAPH_TYPES])
    machines = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")])

    submit = SubmitField('Submit')


class OeeLineForm(FlaskForm):
    graph_name = "OEE Line Graph"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT)
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT)

    submit = SubmitField('Submit')


class DowntimeBarForm(FlaskForm):
    graph_name = "Downtime Bar Chart"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT)
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT)
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight)
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight)
    graph_type = SelectField(choices=[(v, v) for v in GRAPH_TYPES])
    machines = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")])
    dashboard = BooleanField(label="Create Dashboard View")


class JobTableForm(FlaskForm):
    graph_name = "Job Table"
    start_date = DateField(validators=[DataRequired()], format=DATE_FORMAT)
    end_date = DateField(validators=[DataRequired()], format=DATE_FORMAT)
