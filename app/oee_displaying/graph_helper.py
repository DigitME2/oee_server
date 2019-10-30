import operator

from plotly.offline import plot
from plotly.graph_objs import Layout
from plotly.graph_objs.layout import Shape, Annotation
from flask import current_app
from datetime import datetime

from app.data_analysis.oee import calculate_activity_percent
from app.default.models import Activity, Machine, ActivityCode
from app.oee_displaying.helpers import get_machine_status
from config import Config
from app.default.db_helpers import get_current_activity_id
import plotly.figure_factory as ff


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
    layout.autosize = False
    layout.margin = dict(l=100, r=50, b=50, t=50, pad=10)
    return layout


def create_machine_gantt(machine_id, graph_start, graph_end, hide_jobless=False):
    """ Create a gantt chart of the usage of a single machine, between the two timestamps provided"""

    if machine_id is None:
        return "This machine does not exist"

    activities = get_activities(machine_id=machine_id, timestamp_start=graph_start, timestamp_end=graph_end)
    # Sort the activities so that uptime is always the first.
    # This is a workaround to make the graph always show uptime on the bottom
    activities.sort(key=sort_activities, reverse=True)

    df = get_df(activities=activities, group_by="activity_code", graph_start=graph_start, graph_end=graph_end)

    if len(df) == 0:
        return "No machine activity"

    machine = Machine.query.get(machine_id)
    graph_title = f"{machine.name} OEE"

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
                          show_colorbar=True,
                          width=1800)

    # Create a layout object using the layout automatically created
    layout = Layout(fig['layout'])
    layout = apply_default_layout(layout)

    # Highlight jobs
    layout = highlight_jobs(get_activities(machine_id, timestamp_start=graph_start, timestamp_end=graph_end), layout)

    # Pass the changed layout back to fig
    fig['layout'] = layout

    config = {'responsive': True}

    return plot(fig, output_type="div", include_plotlyjs=True, config=config)


def create_multiple_machines_gantt(graph_start, graph_end, machine_ids):
    """ Creates a gantt plot of OEE for all machines in the database between given times
    graph_start = the start time of the graph
    graph_end = the end time of the graph
    machine_ids = a list of ids to include in the graph"""

    activities = []
    machine_ids.sort()
    for machine_id in machine_ids:
        machine_activities = get_activities(machine_id=machine_id, timestamp_start=graph_start, timestamp_end=graph_end)
        # If a machine has no activities, add a fake one so it still shows on the graph
        if len(machine_activities) == 0:
            activities.append(Activity(timestamp_start=graph_start, timestamp_end=graph_start))
        else:
            activities.extend(machine_activities)

    df = get_df(activities=activities,
                group_by="machine_name",
                graph_start=graph_start,
                graph_end=graph_end,
                crop_overflow=True)

    if len(df) == 0:
        return "No machine activity"
    graph_title = "All machines OEE"
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
                          width=1800)

    # Create a layout object using the layout automatically created
    layout = Layout(fig['layout'])
    layout = apply_default_layout(layout)
    fig['layout'] = layout
    return plot(fig, output_type="div", include_plotlyjs=True)


def create_job_end_gantt(job):
    """ Create a gantt chart of the activities for a job, flagging those that need an explanation from an operator"""

    activities = job.activities
    if len(activities) == 0:
        return "No machine activity between these times"

    # Add each activity to a dictionary, to add to the graph
    # Do this in two separate loops so that the first entry in the dictionary is always one requiring an explanation,
    # putting them all on the upper level in the graph (in a roundabout way) There's probably be a better way to do this
    df = []
    annotations = []
    for act in activities:
        if act.explanation_required:
            # If the activity extends past the  start or end, crop it short
            if act.timestamp_start < job.start_time:
                start = job.start_time
            else:
                start = act.timestamp_start
            if act.timestamp_end > job.end_time:
                end = job.end_time
            else:
                end = act.timestamp_end
            df.append(dict(Task=act.explanation_required,
                           Start=datetime.fromtimestamp(start),
                           Finish=datetime.fromtimestamp(end),
                           Code=act.explanation_required,
                           Activity_id=act.id))
            text = "{start}<br>Explanation<br>Required".format(
                start=datetime.fromtimestamp(act.timestamp_start).strftime('%H:%M'))
            position = datetime.fromtimestamp((start + end) / 2)
            annotations.append(dict(x=position, y=1.7, text=text, showarrow=False, font=dict(color='black')))

    # The second loop, for activities not requiring an explanation
    for act in activities:
        if not act.explanation_required:
            # If the activity extends past the  start or end, crop it short
            if act.timestamp_start < job.start_time:
                start = job.start_time
            else:
                start = act.timestamp_start
            if act.timestamp_end > job.end_time:
                end = job.end_time
            else:
                end = act.timestamp_end
            df.append(dict(Task=act.explanation_required,
                           Start=datetime.fromtimestamp(start),
                           Finish=datetime.fromtimestamp(end),
                           Code=act.explanation_required,
                           Activity_id=act.id))

    # Use the colours assigned to uptime and unexplained downtime
    uptime_colour = ActivityCode.query.get(Config.UPTIME_CODE_ID).graph_colour
    unexplained_colour = ActivityCode.query.get(Config.UNEXPLAINED_DOWNTIME_CODE_ID).graph_colour
    colours = {True: unexplained_colour,
               False: uptime_colour}
    fig = ff.create_gantt(df,
                          title="",
                          group_tasks=True,
                          colors=colours,
                          index_col='Code',
                          bar_width=0.4,
                          show_colorbar=False,
                          width=1800)

    layout = Layout(fig['layout'])
    layout = apply_default_layout(layout)

    layout.annotations = annotations
    layout.yaxis.showticklabels = False
    # Pass the changed layout back to fig
    fig['layout'] = layout
    config = {'responsive': True}

    return plot(fig, output_type="div", include_plotlyjs=True, config=config)


def create_dashboard_gantt(graph_start, graph_end, machine_ids, title, include_plotlyjs=True):
    """ Creates a gantt plot of OEE for all machines in the database between given times
    graph_start = the start time of the graph
    graph_end = the end time of the graph
    machine_ids = a list of ids to include in the graph"""

    activities = []
    machine_ids.sort()
    for machine_id in machine_ids:
        activities.extend(get_activities(machine_id=machine_id,
                                         timestamp_start=graph_start,
                                         timestamp_end=graph_end))

    df = get_df(activities=activities,
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
    if len(machine_ids) < 4:
        layout.height = 200 * len(machine_ids)
    else:
        layout.height = None
    layout.width = None
    layout.autosize = True
    layout.margin['l'] = 150  # Create a bigger margin on the left to avoid cutting off title
    layout.margin['pad'] = 1
    layout.yaxis.range = None
    layout.yaxis.autorange = True

    layout.xaxis.range = [datetime.fromtimestamp(graph_start), datetime.fromtimestamp(graph_end)]

    layout.xaxis.rangeselector.visible = False

    new_tick_texts = []
    # Replace the labels on the y axis to show the current user and job
    for machine_id in machine_ids:
        status_dict = get_machine_status(machine_id)
        desired_text = f"{status_dict['machine_name']}<br>" \
                       f"{status_dict['machine_user']}<br>" \
                       f"{status_dict['machine_job']}<br>" \
                       f"{status_dict['machine_activity']}"
        new_tick_texts.append(desired_text)

    # The order of the tick texts in the layout is in the reverse order
    new_tick_texts.reverse()
    layout.yaxis.ticktext = tuple(new_tick_texts)
    #TODO I dont like this method of changing the tick texts. It seems like it's possible to mix up machines
    # as there is nothing currently controlling this

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
        values.append(calculate_activity_percent(machine_id, ac.id, graph_start, graph_end))
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

           'layout': {'title': f"OEE for {machine.name}"}}
    return plot(fig,
                output_type="div",
                include_plotlyjs=True)


def sort_activities(act):
    # Sort so uptime is always first in the list
    if act.activity_code_id == Config.UPTIME_CODE_ID:
        return 0
    if act.activity_code_id == Config.UNEXPLAINED_DOWNTIME_CODE_ID:
        return 1
    return act.activity_code_id


def get_df(activities, group_by, graph_start, graph_end, crop_overflow=True):
    """ Takes a list of machine IDs and returns a dataframe with the activities associated with the machines
    crop_overflow will crop activities that extend past the requested graph start and end times"""

    df = []
    for act in activities:
        # Don't show values outside of graph time range
        if crop_overflow:
            if act.timestamp_start < graph_start:
                start = graph_start
            else:
                start = act.timestamp_start
            if act.timestamp_end is None:
                # Extend the current activity to either graph end or current time
                if graph_end >= datetime.now().timestamp():
                    end = datetime.now().timestamp()
                else:
                    end = graph_end
            elif act.timestamp_end > graph_end:
                end = graph_end
            else:
                end = act.timestamp_end
        # Use actual times if they're not being cropped
        else:
            start = act.timestamp_start
            end = act.timestamp_end

        code = act.activity_code.short_description
        task = operator.attrgetter("machine.name")(act)

        df.append(dict(Task=task,
                       Start=datetime.fromtimestamp(start),
                       Finish=datetime.fromtimestamp(end),
                       Code=code))

    return df


def get_activities(machine_id, timestamp_start, timestamp_end):
    """ Returns the activities for a machine, between two times"""

    machine = Machine.query.get(machine_id)
    if machine is None:
        current_app.logger.warn(f"Activities requested for non-existent Machine ID {machine_id}")
        return
    activities = Activity.query \
        .filter(Activity.machine_id == machine.id) \
        .filter(Activity.timestamp_end >= timestamp_start) \
        .filter(Activity.timestamp_start <= timestamp_end).all()
    # If required, add the current_activity (The above loop will not get it)
    # and extend the end time to the end of the graph

    current_activity_id = get_current_activity_id(target_machine_id=machine.id)
    if current_activity_id is not None:
        current_act = Activity.query.get(current_activity_id)
        # Don't add the current activity if it started after the requested end of the graph
        if current_act.timestamp_start <= timestamp_end:
            activities.append(current_act)

    return activities


def highlight_jobs(activities, layout):
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
            j.end_time = datetime.now().timestamp()

        # Create a shape to highlight each job
        h = Shape()
        h.type = 'rect'
        h.xref = 'x'
        h.yref = 'paper'
        h.x0 = datetime.fromtimestamp(j.start_time)
        h.y0 = 0
        h.x1 = datetime.fromtimestamp(j.end_time)
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
        a.text = f"<b>{j.wo_number}</b>"
        a.font = {
            "size": 16
        }
        a.x = datetime.fromtimestamp((j.start_time + j.end_time) / 2)
        a.yref = 'paper'
        a.y = 0.9
        a.showarrow = False
        a.font.color = 'black'
        annotations.append(a)

    layout.shapes = layout.shapes + tuple(highlights)
    layout.annotations = annotations

    return layout

