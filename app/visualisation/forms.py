from datetime import time

from flask_wtf import FlaskForm
from wtforms import DateField, SubmitField, SelectField, TimeField
from wtforms.validators import DataRequired, NoneOf

from app.default.models import Settings
from app.visualisation.helpers import tomorrow, today, yesterday, a_week_ago

TIME_FORMAT = "%H:%M"
midnight = time(hour=0, minute=0, second=0, microsecond=0)
MACHINES_CHOICES_HEADERS = ["--Groups--", "--Machines--"]

"""

The /data route shows multiple different forms to allow the user to select a graph.

To add a new graph, a new form must be created. 
Extend the base form classes to use one with simple dates/times
Code must be added in visualisation/routes.py to add the form to the list of forms, and to handle submitting.

the forms use a template stub from form_templates.html. These can be set with form_template in the form class.
"date" only shows the date, and "key_date" shows a dropdown as well (for example select which machine to add)

"""


class BaseDatesForm(FlaskForm):
    def __init__(self):
        super().__init__()
        # Set the ID differently per class, so they don't have the same ID on the web page (this breaks datepicker)
        self.start_date.id = self.get_class_name() + "-start-date"
        self.end_date.id = self.get_class_name() + "-end-date"

    @classmethod
    def get_class_name(cls):
        return cls.__name__.lower()

    form_template = "date"
    start_date = DateField(validators=[DataRequired()], label="Start Date", default=a_week_ago)
    end_date = DateField(validators=[DataRequired()], label="End Date", default=yesterday)
    submit = SubmitField('Submit')


class BaseSingleDateForm(FlaskForm):
    def __init__(self):
        super().__init__()
        # Set the ID differently per class, so they don't have the same ID on the web page (this breaks datepicker)
        self.date.id = self.get_class_name() + "-date"

    @classmethod
    def get_class_name(cls):
        return cls.__name__.lower()

    form_template = "single_date"
    date = DateField(validators=[DataRequired()], label="Date", default=today)
    submit = SubmitField('Submit')


class BaseTimeAndDatesForm(FlaskForm):
    def __init__(self):
        super().__init__()
        # Set the ID differently per class, so they don't have the same ID on the web page (this breaks datepicker)
        self.start_date.id = self.get_class_name() + "-start-date"
        self.end_date.id = self.get_class_name() + "-end-date"

    @classmethod
    def get_class_name(cls):
        return cls.__name__.lower()

    start_date = DateField(validators=[DataRequired()], label="Start Date", default=today)
    end_date = DateField(validators=[DataRequired()], label="End Date", default=tomorrow)
    start_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="gantt_start_time")
    end_time = TimeField(validators=[DataRequired()], format=TIME_FORMAT, default=midnight, id="gantt_end_time")
    submit = SubmitField('Submit')


class OeeTableForm(BaseSingleDateForm):
    graph_name = "OEE Report"
    description = "A table showing the a report for each machine on a specified day"


class OeeDateRangeForm(BaseDatesForm):
    graph_name = "Daily OEE Table"
    description = "A table showing the daily OEE figure of all machines between two dates"


class ProdTableForm(BaseDatesForm):
    graph_name = "Daily Production"
    description = "A table showing daily production numbers for each machine"


class GanttForm(BaseTimeAndDatesForm):
    form_template = "key_date_time"
    graph_name = "Machine Status Gantt Chart"
    description = "A Gantt chart showing the activity of a single machine or multiple machines. " \
                  "Time is plotted on the x-axis and different colours represent different activities."
    key = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")],
                      id="gantt_machines")


class OeeLineForm(BaseDatesForm):
    form_template = "key_date"
    graph_name = "OEE Line Graph"
    description = "A line graph showing the daily OEE figure of machines between two dates"
    key = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")],
                      id="oee_machines")


class OeeGroupLineForm(OeeLineForm):
    form_template = "date"
    graph_name = "Machine group OEE Line Graph"
    description = "A line graph showing the daily OEE figure of every machine group between two dates"


class DowntimeBarForm(BaseTimeAndDatesForm):
    form_template = "key_date_time"
    graph_name = "Downtime Bar Chart"
    description = "A bar chart showing the total amount of each activity for selected machines between two times"
    key = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")],
                      id="downtime_bar_machines")


class JobTableForm(BaseDatesForm):
    form_template = "key_date"
    graph_name = "Jobs"
    key = SelectField(validators=[NoneOf(MACHINES_CHOICES_HEADERS, message="Pick a machine or group")],
                      id="job_machines")


class WOTableForm(BaseDatesForm):
    form_template = "date"
    graph_name = "Work Order Table"


class ActivityDurationsTableForm(BaseTimeAndDatesForm):
    form_template = "key_date_time"
    graph_name = "Activity Durations"
    description = "A table showing the total durations of each machine"
    key = SelectField(validators=[DataRequired()], choices=[("users", "Users"), ("machines", "Machines")])
