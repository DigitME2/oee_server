from plotly.offline import plot
from datetime import datetime
from app.default.models import Activity, Machine, UPTIME_CODE

import pandas as pd
import plotly.figure_factory as ff


def create_machine_gantt(machine, graph_start, graph_end):
    """ Create a gantt chart of the usage of a single machine, between the two timestamps provided"""

    # Get the machine's activities between the two times
    activities = Activity.query \
        .filter(Activity.machine_id == machine.id) \
        .filter(Activity.timestamp_end >= graph_start) \
        .filter(Activity.timestamp_start <= graph_end).all()
    if len(activities) == 0:
        return "No machine activity between these times"

    # Add each activity to a dictionary, to add to the graph
    df = []
    for activity in activities:
        # If the activity extends past the  start or end, crop it short
        if activity.timestamp_start < graph_start:
            start = graph_start
        else:
            start = activity.timestamp_start
        if activity.timestamp_end > graph_end:
            end = graph_end
        else:
            end = activity.timestamp_end
        df.append(dict(Task=activity.code.short_description,
                       Start=datetime.fromtimestamp(start),
                       Finish=datetime.fromtimestamp(end),
                       Code=activity.code.short_description,
                       Activity_id=activity.id,
                       hoverinfo="test"))

    graph_title = "{machine_name} OEE".format(machine_name=machine.name)
    colours = {'unexplained': 'rgb(128, 128, 128)',
               'uptime': 'rgb(0, 255, 128)',
               'error1': 'rgb(255,64,0)',
               'error2': 'rgb(255,0,0)',
               'error3': 'rgb(255,255,0)'}
    fig = ff.create_gantt(df,
                          title=graph_title,
                          group_tasks=True,
                          colors=colours,
                          index_col='Code',
                          bar_width=0.4,
                          show_colorbar=True,
                          width=1800)

    # layout = Layout()
    # layout.xaxis.rangeselector.visible = False
    # fig['layout'] = layout

    # Hide the range selector
    fig['layout']['xaxis']['rangeselector']['visible'] = False
    fig['layout']['annotations'] = [dict(x='2009-02-01', y=0, text="This is a label", showarrow=False, font=dict(color='white'))]
    return plot(fig, output_type="div", include_plotlyjs=True)


def create_all_machines_gantt(graph_start, graph_end):
    """ Creates a gantt plot of OEE for all machines in the database between given times"""
    machines = Machine.query.all()
    df = []
    for machine in machines:
        activities = Activity.query \
            .filter(Activity.machine_id == machine.id) \
            .filter(Activity.timestamp_end >= graph_start) \
            .filter(Activity.timestamp_start <= graph_end).all()
        for activity in activities:
            # Don't show values outside of graph time range
            if activity.timestamp_start < graph_start:
                start = graph_start
            else:
                start = activity.timestamp_start
            if activity.timestamp_end > graph_end:
                end = graph_end
            else:
                end = activity.timestamp_end

            # This graph only deals with uptime and not-uptime
            if activity.activity_code == UPTIME_CODE:
                code = 1
            else:
                code = 2
            # Add the activity as a dict to the data fields list
            df.append(dict(Task=machine.name,
                           Start=datetime.fromtimestamp(start),
                           Finish=datetime.fromtimestamp(end),
                           Code=code))
    graph_title = "All machines OEE"
    colours = {1: 'rgb(0, 200, 64)', 2: 'rgb(255,32,0)'}
    fig = ff.create_gantt(df,
                          title=graph_title,
                          group_tasks=True,
                          colors=colours,
                          index_col='Code',
                          bar_width=0.4,
                          width=1800)

    # Hide the range selector
    fig['layout']['xaxis']['rangeselector']['visible'] = False
    return plot(fig, output_type="div", include_plotlyjs=True)
