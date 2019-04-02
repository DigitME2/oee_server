from plotly.offline import plot
from plotly.graph_objs import Layout
from plotly.graph_objs.layout import Shape, Annotation
from datetime import datetime
from app.default.models import Activity, Machine, ActivityCode
from app.default.models import UPTIME_CODE_ID, UNEXPLAINED_DOWNTIME_CODE_ID, MACHINE_STATE_RUNNING
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


def create_machine_gantt(machine, graph_start, graph_end, hide_jobless=False):
    """ Create a gantt chart of the usage of a single machine, between the two timestamps provided"""

    if machine is None:
        return "This machine does not exist"

    # Get the machine's activities between the two times
    activities = Activity.query \
        .filter(Activity.machine_id == machine.id) \
        .filter(Activity.timestamp_end >= graph_start) \
        .filter(Activity.timestamp_start <= graph_end).all()
    act_codes = ActivityCode.query.all()
    if len(activities) == 0:
        return "No machine activity"

    activities.sort(key=sort_activities, reverse=True)

    # Add each activity to a dictionary, to add to the graph
    df = []
    for act in activities:
        # Skip activities without a job, if requested
        if hide_jobless:
            if not act.job_id.any():
                continue
        # If the activity extends past the  start or end, crop it short
        if act.timestamp_start < graph_start:
            start = graph_start
        else:
            start = act.timestamp_start
        if act.timestamp_end > graph_end:
            end = graph_end
        else:
            end = act.timestamp_end
        df.append(dict(Task=act.activity_code.code,
                       Start=datetime.fromtimestamp(start),
                       Finish=datetime.fromtimestamp(end),
                       Code=act.activity_code.short_description,
                       Activity_id=act.id))

    graph_title = "{machine_name} OEE".format(machine_name=machine.name)

    # Create the colours dictionary using codes' colours from the database
    colours = {}
    for act_code in act_codes:
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
    layout = highlight_jobs(activities, layout)

    # Pass the changed layout back to fig
    fig['layout'] = layout

    config = {'responsive': True}

    return plot(fig, output_type="div", include_plotlyjs=True, config=config)


def create_all_machines_gantt(graph_start, graph_end):
    """ Creates a gantt plot of OEE for all machines in the database between given times"""
    machines = Machine.query.all()
    if len(machines) == 0:
        return "No machines found"
    df = []
    for machine in machines:
        activities = Activity.query \
            .filter(Activity.machine_id == machine.id) \
            .filter(Activity.timestamp_end >= graph_start) \
            .filter(Activity.timestamp_start <= graph_end).all()
        for act in activities:
            # Don't show values outside of graph time range
            if act.timestamp_start < graph_start:
                start = graph_start
            else:
                start = act.timestamp_start
            if act.timestamp_end > graph_end:
                end = graph_end
            else:
                end = act.timestamp_end

            # This graph only deals with running and not running
            if act.machine_state == MACHINE_STATE_RUNNING:
                code = 1
            else:
                code = 2
            # Add the activity as a dict to the data fields list
            df.append(dict(Task=machine.name,
                           Start=datetime.fromtimestamp(start),
                           Finish=datetime.fromtimestamp(end),
                           Code=code))
    if len(df) == 0:
        return "No machine activity"
    graph_title = "All machines OEE"
    colours = {1: ActivityCode.query.get(UPTIME_CODE_ID).graph_colour,
               2: ActivityCode.query.get(UNEXPLAINED_DOWNTIME_CODE_ID).graph_colour}
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


def create_shift_end_gantt(activities):
    """ Create a gantt chart of the activities provided. Intended to be used for one machine only"""

    if len(activities) == 0:
        return "No machine activity between these times"

    # Add each activity to a dictionary, to add to the graph
    # Do this in two separate loops so that the entries requiring explanation are first in the dictionary, putting
    #  them on the upper level in the graph (in a roundabout way) There's probably be a better way to do this via plotly
    df = []
    annotations = []
    for act in activities:
        if act.explanation_required:
            start = act.timestamp_start
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

    for act in activities:
        if not act.explanation_required:
            start = act.timestamp_start
            end = act.timestamp_end
            df.append(dict(Task=act.explanation_required,
                           Start=datetime.fromtimestamp(start),
                           Finish=datetime.fromtimestamp(end),
                           Code=act.explanation_required,
                           Activity_id=act.id))

    # Use the colours assigned to uptime and unexplained downtime
    uptime_colour = ActivityCode.query.get(UPTIME_CODE_ID).graph_colour
    unexplained_colour = ActivityCode.query.get(UNEXPLAINED_DOWNTIME_CODE_ID).graph_colour
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
            # If the job doesn't have an end time, use the latest activity end time as its end time
            j.end_time = j.start_time
            for act in j.activities:
                if act.timestamp_end > j.end_time:
                    j.end_time = act.timestamp_end

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
        a.text = "<b>Job {job_number}</b>".format(job_number=j.job_number)
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


def sort_activities(act):
    # Sort so uptime is always first in the list
    if act.activity_code_id == UPTIME_CODE_ID:
        return 0
    if act.activity_code_id == UNEXPLAINED_DOWNTIME_CODE_ID:
        return 1
    return act.activity_code_id
