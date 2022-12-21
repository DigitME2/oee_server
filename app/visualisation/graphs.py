import operator
from datetime import datetime, timedelta, date
from logging import getLogger
from typing import List

import plotly.figure_factory as ff
import plotly.graph_objects as go
from plotly.graph_objs import Layout
from plotly.graph_objs.layout import Shape, Annotation
from plotly.offline import plot

from app.data_analysis.oee.availability import get_activity_duration_dict
from app.data_analysis.oee.oee import get_daily_machine_oee
from app.default.helpers import get_machine_activities, get_activity_cropped_start_end
from app.default.models import Activity, Machine, ActivityCode, Settings
from app.visualisation.helpers import get_machine_status
from config import Config

logger = getLogger()


SCHEDULED_UPTIME_KEY_STRING = "Scheduled uptime"
SCHEDULED_DOWNTIME_KEY_STRING = "Scheduled downtime"


def apply_default_layout(layout):
    layout.xaxis.rangeselector.buttons = [
        dict(count=1,
             label='1h',
             step='hour',
             stepmode='backward'),
        dict(count=3,
             label='3h',
             step='hour',
             stepmode='backward'),
        dict(count=6,
             label='6h',
             step='hour',
             stepmode='backward'),
        dict(step='all')]
    layout.showlegend = False
    layout.xaxis.showline = True
    layout.yaxis.tickfont = {
        'size': 16
    }
    layout.xaxis.rangeselector.visible = False
    layout.autosize = True
    layout.margin = dict(l=100, r=50, b=50, t=50, pad=10)
    return layout


def create_machine_gantt(machine,
                         graph_start: datetime,
                         graph_end: datetime,
                         hide_jobless=False,
                         highlight_jobs=False):
    """ Create a gantt chart of the usage of a single machine, between the two times provided"""

    if machine is None:
        return "This machine does not exist"

    activities = get_machine_activities(machine=machine, time_start=graph_start, time_end=graph_end)
    # Sort the activities so that uptime is always the first.
    # This is a workaround to make the graph always show uptime on the bottom
    activities.sort(key=sort_activities, reverse=True)

    df = get_activities_df(activities=activities, group_by="activity_code", graph_start=graph_start,
                           graph_end=graph_end)

    if len(df) == 0:
        return "No machine activity"

    graph_title = f"{machine.name}"

    # Create the colours dictionary using codes' colours from the database
    colours = {}
    for act_code in ActivityCode.query.all():
        colours[act_code.short_description] = act_code.graph_colour

    fig = ff.create_gantt(df,
                          title=graph_title,
                          group_tasks=True,
                          colors=colours,
                          index_col='Code',
                          bar_width=0.4,
                          show_colorbar=True)

    # Create a layout object using the layout automatically created
    layout = Layout(fig['layout'])
    layout = apply_default_layout(layout)
    layout.showlegend = True

    # Highlight jobs
    if highlight_jobs:
        layout = highlight_jobs_on_gantt_layout(activities, layout)

    # Pass the changed layout back to fig
    fig['layout'] = layout
    config = {'responsive': True}
    return plot(fig, output_type="div", include_plotlyjs=True, config=config)


def create_multiple_machines_gantt(graph_start: datetime, graph_end: datetime, machines):
    """ Creates a gantt plot of activities for all machines in the database between given times
    graph_start = the start time of the graph
    graph_end = the end time of the graph
    machine_ids = a list of ids to include in the graph"""

    activities = []
    machines.sort(key=lambda m: m.id)
    for machine in machines:
        machine_activities = get_machine_activities(machine=machine, time_start=graph_start,
                                                    time_end=graph_end)
        activities.extend(machine_activities)

    df = get_activities_df(activities=activities,
                           group_by="machine_name",
                           graph_start=graph_start,
                           graph_end=graph_end,
                           crop_overflow=True)

    if len(df) == 0:
        return "No machine activity"
    # Create the colours dictionary using codes' colours from the database
    colours = {}
    for act_code in ActivityCode.query.all():
        colours[act_code.short_description] = act_code.graph_colour
    fig = ff.create_gantt(df,
                          group_tasks=True,
                          colors=colours,
                          index_col='Code',
                          bar_width=0.4)

    # Create a layout object using the layout automatically created
    layout = Layout(fig['layout'])
    layout = apply_default_layout(layout)
    layout.showlegend = True
    fig['layout'] = layout
    config = {'responsive': True}
    return plot(fig, output_type="div", include_plotlyjs=True, config=config)


def create_dashboard_gantt(graph_start: datetime, graph_end: datetime, machines, title, include_plotlyjs=True):
    """ Creates a gantt plot of activities for all machines in the database between given times
    graph_start = the start time of the graph
    graph_end = the end time of the graph
    machine_ids = a list of ids to include in the graph"""

    activities = []
    machines.sort(key=lambda m: m.id)
    for machine in machines:
        activities.extend(get_machine_activities(machine=machine,
                                                 time_start=graph_start,
                                                 time_end=graph_end))

    df = get_activities_df(activities=activities,
                           group_by="machine_name",
                           graph_start=graph_start,
                           graph_end=graph_end,
                           crop_overflow=True)

    if len(df) == 0:
        return "No machine activity"

    # Create the colours dictionary using codes' colours from the database
    colours = {}
    for act_code in ActivityCode.query.all():
        colours[act_code.short_description] = act_code.graph_colour
    fig = ff.create_gantt(df,
                          title=title,
                          group_tasks=True,
                          colors=colours,
                          index_col='Code',
                          bar_width=0.4,
                          width=1800)

    # Create a layout object using the layout automatically created
    layout = Layout(fig['layout'])
    layout = apply_default_layout(layout)

    # Lower the height when there are only a few machines, to stop the bar being stretched vertically
    # Minor bug: If there are machines without activities, they'll still count here but wont show on the graph
    if len(machines) < 4:
        layout.height = 200 * len(machines)
    else:
        layout.height = None
    layout.width = None
    layout.autosize = True
    layout.margin['l'] = 150  # Create a bigger margin on the left to avoid cutting off title
    layout.margin['pad'] = 1
    layout.yaxis.range = None
    layout.yaxis.autorange = True

    layout.xaxis.range = [graph_start, graph_end]

    layout.xaxis.rangeselector.visible = False

    new_tick_texts = []
    # Replace the labels on the y axis to show the current user and job
    for machine in machines:
        status_dict = get_machine_status(machine)
        desired_text = f"{status_dict['machine_name']}<br>" \
                       f"{status_dict['machine_user']}<br>" \
                       f"{status_dict['machine_job']}<br>" \
                       f"{status_dict['machine_activity']}"
        new_tick_texts.append(desired_text)

    # The order of the tick texts in the layout is in the reverse order
    new_tick_texts.reverse()
    layout.yaxis.ticktext = tuple(new_tick_texts)

    # Change the text sizes
    layout.yaxis.tickfont.size = 18
    layout.xaxis.tickfont.size = 18
    layout.titlefont.size = 24

    fig['layout'] = layout

    return plot(fig,
                output_type="div",
                include_plotlyjs=include_plotlyjs,
                config={"displayModeBar": False, "showLink": False})


def create_downtime_pie(machine_id, graph_start, graph_end):
    machine = Machine.query.get_or_404(machine_id)
    labels = []
    values = []
    colours = []
    for ac in ActivityCode.query.all():
        labels.append(ac.short_description)
        # values.append(calculate_activity_percent(machine_id, ac.id, graph_start, graph_end))
        colours.append(ac.graph_colour)

    layout = Layout(title=f"OEE for {machine.name}", )

    fig = {'data': [{'type': 'pie',
                     'name': f"OEE for {machine.name}",
                     'labels': labels,
                     'values': values,
                     'direction': 'clockwise',
                     'textposition': 'inside',
                     'textinfo': 'label+percent',
                     'marker': {'colors': colours}}],

           'layout': layout}
    return plot(fig,
                output_type="div",
                include_plotlyjs=True)


def create_oee_line(graph_start_date: date, graph_end_date: date, machines):
    """ Takes two times and creates a line graph of the OEE for each machine between these times
    The graph contains values for all time, but zooms in on the given dates. This allows scrolling once the graph is made"""
    d = Settings.query.get(1).first_start.date()
    dates = [d + timedelta(days=x) for x in range((graph_end_date - d).days + 1)]
    if len(dates) == 0:
        return 0
    fig = go.Figure()
    machines.sort(key=lambda m: m.id)
    for machine in machines:
        machine_oee_figures = []
        for d in dates:
            machine_oee_figures.append(get_daily_machine_oee(machine=machine, date=d))
        fig.add_trace(go.Scatter(x=dates, y=machine_oee_figures, name=machine.name, mode='lines+markers'))

    layout = Layout()
    layout.xaxis.update(range=[graph_start_date, graph_end_date])
    layout.xaxis.tickformat = '%a %d-%m-%Y'
    layout.xaxis.showgrid = False
    layout.xaxis.dtick = 86400000  # Space between ticks = 1 day
    fig.layout = layout

    return plot(fig,
                output_type="div",
                include_plotlyjs=True,
                config={"showLink": False})


def create_downtime_bar(machines, graph_start: datetime, graph_end: datetime):
    total_activities_dict = None
    for machine in machines:
        activities_dict = get_activity_duration_dict(requested_start=graph_start,
                                                     requested_end=graph_end,
                                                     machine=machine,
                                                     use_description_as_key=True,
                                                     units="minutes")

        if not total_activities_dict:
            # Use the first value to start the dict
            total_activities_dict = activities_dict
        else:
            for n in total_activities_dict:
                total_activities_dict[n] += activities_dict[n]

    activity_code_names = list(total_activities_dict.keys())
    activity_code_durations = list(total_activities_dict.values())
    fig = go.Figure([go.Bar(x=activity_code_names, y=activity_code_durations)])
    fig.layout.title = "Total Time (Minutes)"
    return plot(fig,
                output_type="div",
                include_plotlyjs=True,
                config={"showLink": False})


def sort_activities(act):
    # Sort so uptime is always first in the list
    if act.activity_code_id == Config.UPTIME_CODE_ID:
        return 0
    if act.activity_code_id == Config.UNEXPLAINED_DOWNTIME_CODE_ID:
        return 1
    return act.activity_code_id


def get_activities_df(activities: List[Activity], group_by, graph_start: datetime, graph_end: datetime, crop_overflow=True):
    """ Takes a list of machine IDs and returns a dataframe with the activities associated with the machines
    crop_overflow will crop activities that extend past the requested graph start and end times"""

    df = []
    for act in activities:
        if not act.activity_code:
            logger.warning("Found activity without activity code ID=" + str(act.id))
            continue
        # Don't show values outside of graph time range
        if crop_overflow:
            start, end = get_activity_cropped_start_end(act, graph_start, graph_end)
        # Use actual times if they're not being cropped
        else:
            start = act.time_start
            end = act.time_end
        code = act.activity_code.short_description

        task = operator.attrgetter("machine.name")(act)

        df.append(dict(Task=task,
                       Start=start,
                       Finish=end,
                       Code=code))

    return df


def highlight_jobs_on_gantt_layout(activities, layout):
    """ Creates 'highlight' shapes to show the times of jobs on the graph"""
    # Get all of the jobs from the activities
    jobs = []
    for act in activities:
        if act.job is None:
            continue
        if act.job not in jobs:
            jobs.append(act.job)

    highlights = []
    annotations = []
    for j in jobs:
        if j.end_time is None:
            # If the job doesn't have an end time, use the current time as its end time
            j.end_time = datetime.now()

        # Create a shape to highlight each job
        h = Shape()
        h.type = 'rect'
        h.xref = 'x'
        h.yref = 'paper'
        h.x0 = j.start_time
        h.y0 = 0
        h.x1 = j.end_time
        h.y1 = 0.9
        h.fillcolor = '#C0C0C0'
        h.opacity = 0.3
        h.visible = True
        h.line = {
            'width': 1
        }
        highlights.append(h)

        # Create an annotation at the top of the highlight saying the job number
        a = Annotation()
        a.text = f"<b>{j.job_number}</b>"
        a.font = {
            "size": 16
        }
        a.x = j.start_time + ((j.start_time - j.end_time) / 2)
        a.yref = 'paper'
        a.y = 0.9
        a.showarrow = False
        a.font.color = 'black'
        annotations.append(a)

    layout.shapes = layout.shapes + tuple(highlights)
    layout.annotations = annotations

    return layout
