from datetime import datetime, timedelta, time

import plotly.graph_objects as go
from flask import abort, request, render_template, current_app
from flask_login import login_required
from flask_wtf import FlaskForm
from plotly.graph_objs import Layout
from plotly.offline import plot
from sqlalchemy import inspect
from wtforms import DateField, SubmitField, SelectField, DateTimeField, DateTimeLocalField
from wtforms.validators import DataRequired

from app.data_analysis.oee.availability import get_machine_availability, get_activity_duration_dict, \
    calculate_activity_percent
from app.data_analysis.oee.models import DailyOEE
from app.data_analysis.oee.oee import get_daily_machine_oee, get_daily_group_oee
from app.data_analysis.oee.performance import get_machine_performance
from app.data_analysis.oee.quality import get_machine_quality
from app.default.models import Machine, MachineGroup, Settings, ScheduledActivity, Job, Activity, ActivityCode

from app.extensions import db
from app.login.models import UserSession
from app.visualisation import bp
from app.visualisation.forms import MACHINES_CHOICES_HEADERS, GanttForm, OeeLineForm, \
    DowntimeBarForm, JobTableForm, \
    WOTableForm, RawDatabaseTableForm, ActivityDurationsTableForm, SchedulesGanttForm, OeeTableForm, ProdTableForm
from app.visualisation.graphs import create_machine_gantt, create_multiple_machines_gantt, \
    create_dashboard_gantt, create_downtime_bar, create_schedules_gantt, create_oee_line
from app.visualisation.helpers import parse_requested_machine_list, today, tomorrow
from app.visualisation.tables import get_work_order_table, get_job_table, get_raw_database_table, \
    get_user_activity_table, get_machine_activity_table, get_oee_table, get_machine_production_table


# --------------- APQ GRAPH CODE -------------------------------

class APQForm(FlaskForm):
    start_date = DateField(validators=[DataRequired()], label="Start Date (YYYY-MM-DD)", default=today)
    end_date = DateField(validators=[DataRequired()], label="End Date (YYYY-MM-DD)", default=tomorrow)

    key = SelectField(validators=[DataRequired()],
                      id="oee_machines")
    submit = SubmitField('Submit')


class JPQForm(FlaskForm):
    start_date = DateTimeField(validators=[DataRequired()], format="%Y-%m-%d",label="Start Date (YYYY-MM-DD)")
    end_date = DateTimeField(validators=[DataRequired()],  format="%Y-%m-%d",label="End Date (YYYY-MM-DD)")

    key = SelectField(validators=[DataRequired()],
                      id="oee_machines")
    submit = SubmitField('Submit')








@bp.route('/apq-graph', methods=['GET', 'POST'])
def apq():

    # Get a list of machines to provide a dropdown
    machines = Machine.query.all()

    machine_name_choices = [(str(m.id), m.name) for m in machines]
    #user_session = [ (str(ud.id), ud.time_login) for ud in UserSession.quary.all()]



    # Create the form
    form = APQForm()
    form.key.choices = machine_name_choices
    #form.start_date.choice = user_session
    print(form.key.choices)


    # If the form has been submitted we need to create the graph
    if form.validate_on_submit():
        # Parse the machine we want from the form, and the start and end date of the graph
        machine_ids = [form.key.data]

        graph_start_date = form.start_date.data,
        graph_end_date = form.end_date.data

        # Get a list of dates to use as X axis
        d = Settings.query.get(1).first_start.date()
        dates = [d + timedelta(days=x) for x in range((graph_end_date - d).days + 1)]
        print(dates)
        if len(dates) == 0:
            return 0
        fig = go.Figure()
       # print('/n',fig)


        # Loop through the machines and get the OEE figure for each machine
        machine_ids.sort()
        print(machine_ids.sort())
        for machine_id in machine_ids:
            machine = Machine.query.get(machine_id)



            machine_oee_figures = []
            machine_oee_availability=[]




            for d in dates:
                machine_oee_figures.append(get_daily_machine_oee(machine_id=machine_id, date=d))
                machine_oee_availability.append(get_machine_availability(machine_id=machine_id,
                                                                         time_start=datetime.combine(date=d,time=time(0,0,0)),
                                                                         time_end=datetime.combine(date=d,time=time(23,59,59))))






            # Add the trace to the graph
            fig.add_trace(go.Line(x=dates, y=machine_oee_figures, name=machine.name+' OEE', mode='markers+lines'))
            fig.add_trace(go.Scatter(x=dates, y=machine_oee_availability, name=machine.name + ' Availability',
                                     mode='lines+markers'))



        # Modify the layout
        layout = Layout()
        layout.update({'title':'OEE', 'height':500, 'width':800})
        layout.xaxis.update(range=[graph_start_date, graph_end_date])
        layout.xaxis.tickformat = '%a %d-%m-%Y'
        layout.xaxis.showgrid = True
        layout.xaxis.dtick = 86400000  # Space between ticks = 1 day
        #layout.yaxis.update(range=[0,24])
        fig.layout = layout
        print('\n',layout)


        # Plot the graph
        graph = plot(fig,
                     output_type="div",
                     include_plotlyjs=True,
                     config={"showLink": False})
        #print('\n',graph)
    else:
        graph = None

    return render_template("oee_displaying/apq_graph.html",
                           form=form,
                           graph=graph)






@bp.route('/data', methods=['GET', 'POST'])
@login_required
def data():
    """ The page showing options for data output"""
    # Get each machine
    machines = Machine.query.all()

    # Put the machine and group names into a ("str", "str") tuple as required by wtforms selectfield
    # The list returns m_1 for machine with id 1, and g_2 for a group with id 2
    machine_name_choices = [("m_" + str(m.id), m.name) for m in machines]
    group_name_choices = [("g_" + str(mg.id), mg.name) for mg in MachineGroup.query.all()]
    machines_choices = [("all", "All Machines")] + \
                       [(MACHINES_CHOICES_HEADERS[0], MACHINES_CHOICES_HEADERS[0])] + group_name_choices + \
                       [(MACHINES_CHOICES_HEADERS[1], MACHINES_CHOICES_HEADERS[1])] + machine_name_choices

    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    table_name_choices = [(table_name, table_name) for table_name in table_names]

    gantt_form = GanttForm()
    gantt_form.key.choices = machines_choices

    oee_line_form = OeeLineForm()
    oee_line_form.key.choices = machines_choices

    oee_table_form = OeeTableForm()

    prod_table_form = ProdTableForm()

    downtime_bar_form = DowntimeBarForm()
    downtime_bar_form.key.choices = machines_choices

    schedule_gantt_form = SchedulesGanttForm()
    schedule_gantt_form.key.choices = machines_choices

    job_table_form = JobTableForm()
    job_table_form.key.choices = machines_choices
    wo_table_form = WOTableForm()
    activity_table_form = ActivityDurationsTableForm()
    raw_db_table_form = RawDatabaseTableForm()
    raw_db_table_form.key.choices = table_name_choices

    forms = [gantt_form, oee_line_form, oee_table_form, prod_table_form, downtime_bar_form, job_table_form,
             activity_table_form,
             schedule_gantt_form]

    # Check which form has been sent by the user
    form_sent = next((form for form in forms if form.__class__.__name__ == request.form.get('formType')), None)
    if isinstance(form_sent, GanttForm) and gantt_form.validate_on_submit():
        start = datetime.combine(date=gantt_form.start_date.data, time=gantt_form.start_time.data)
        end = datetime.combine(date=gantt_form.end_date.data, time=gantt_form.end_time.data)
        machine_ids = parse_requested_machine_list(gantt_form.key.data)
        if len(machine_ids) == 1:
            graph = create_machine_gantt(machine_id=machine_ids[0],
                                         graph_start=start,
                                         graph_end=end)
        else:
            graph = create_multiple_machines_gantt(machine_ids=machine_ids,
                                                   graph_start=start,
                                                   graph_end=end)

    elif isinstance(form_sent, OeeLineForm) and oee_line_form.validate_on_submit():
        machine_ids = parse_requested_machine_list(downtime_bar_form.key.data)
        graph = create_oee_line(graph_start_date=oee_line_form.start_date.data,
                                graph_end_date=oee_line_form.end_date.data,
                                machine_ids=machine_ids)

    elif isinstance(form_sent, OeeTableForm) and oee_table_form.validate_on_submit():
        graph = get_oee_table(start_date=oee_table_form.start_date.data,
                              end_date=oee_table_form.end_date.data)

    elif isinstance(form_sent, ProdTableForm) and prod_table_form.validate_on_submit():
        graph = get_machine_production_table(start_date=prod_table_form.start_date.data,
                                             end_date=prod_table_form.end_date.data)

    elif isinstance(form_sent, DowntimeBarForm) and downtime_bar_form.validate_on_submit():
        start = datetime.combine(date=downtime_bar_form.start_date.data, time=downtime_bar_form.start_time.data)
        end = datetime.combine(date=downtime_bar_form.end_date.data, time=downtime_bar_form.end_time.data)
        machine_ids = parse_requested_machine_list(downtime_bar_form.key.data)
        graph = create_downtime_bar(machine_ids=machine_ids,
                                    graph_start=start,
                                    graph_end=end)

    elif isinstance(form_sent, JobTableForm) and job_table_form.validate_on_submit():
        machine_ids = parse_requested_machine_list(job_table_form.key.data)
        graph = get_job_table(start_date=job_table_form.start_date.data,
                              end_date=job_table_form.end_date.data,
                              machine_ids=machine_ids)

    elif isinstance(form_sent, WOTableForm) and wo_table_form.validate_on_submit():
        graph = get_work_order_table(start_date=wo_table_form.start_date.data,
                                     end_date=wo_table_form.end_date.data)

    elif isinstance(form_sent, ActivityDurationsTableForm) and activity_table_form.validate_on_submit():
        start = datetime.combine(date=downtime_bar_form.start_date.data, time=downtime_bar_form.start_time.data)
        end = datetime.combine(date=downtime_bar_form.end_date.data, time=downtime_bar_form.end_time.data)
        if "users" in activity_table_form.key.data:
            graph = get_user_activity_table(time_start=start, time_end=end)
        elif "machines" in activity_table_form.key.data:
            graph = get_machine_activity_table(time_start=start, time_end=end)
        else:
            graph = "Error"

    elif isinstance(form_sent, RawDatabaseTableForm) and raw_db_table_form.validate_on_submit():
        graph = get_raw_database_table(table_name=raw_db_table_form.key.data)

    elif isinstance(form_sent, SchedulesGanttForm) and schedule_gantt_form.validate_on_submit():
        start = datetime.combine(date=schedule_gantt_form.start_date.data, time=schedule_gantt_form.start_time.data)
        end = datetime.combine(date=schedule_gantt_form.end_date.data, time=schedule_gantt_form.end_time.data)
        machine_ids = parse_requested_machine_list(schedule_gantt_form.key.data)
        graph = create_schedules_gantt(machine_ids=machine_ids,
                                       graph_start=start,
                                       graph_end=end)

    else:
        graph = ""

    return render_template('oee_displaying/data.html',
                           machines=machines,
                           nav_bar_title="Graphs",
                           forms=forms,
                           graph=graph,
                           last_form=form_sent)


@bp.route('/create-dashboard')
def create_dashboard():
    machine_groups = MachineGroup.query.all()
    return render_template("oee_displaying/create_dashboard.html",
                           groups=machine_groups)


@bp.route('/dashboard')
def dashboard():
    # Get the update interval to send to the page
    update_interval_seconds = Settings.query.get(1).dashboard_update_interval_s
    update_interval_ms = update_interval_seconds * 1000  # The jquery function takes milliseconds

    # Get the group of machines to show
    if 'machine_group' not in request.args:
        current_app.logger.warn(f"Request arguments {request.args} do not contain a machine_group")
        return abort(400, "No machine_group provided in url")
    requested_machine_group = request.args['machine_group']
    machine_group = MachineGroup.query.filter_by(name=requested_machine_group).first()
    if not machine_group:
        # try selecting by ID
        machine_group = MachineGroup.query.get(int(requested_machine_group))
        if not machine_group:
            return abort(400, "Could not find that machine group")
    machines = machine_group.machines
    machine_ids = list(machine.id for machine in machines)

    graph_title = machine_group.name

    # If start is given in the url arguments, start the graph at that time on today's date
    # Start should be in the format HH:MM
    if 'start' in request.args:
        start_time = datetime.strptime(request.args['start'], "%H:%M")
        start = datetime.now().replace(hour=start_time.hour, minute=start_time.minute)
        start = start - timedelta(minutes=1)  # Quick hack to make sure the start time shows on the x axis
    # If no start given, start at 8am
    else:
        start = datetime.now().replace(hour=8)

    # If 'end' is in the url arguments, end the graph at that time on today's date
    if 'end' in request.args:
        end_time = datetime.strptime(request.args['end'], "%H:%M")
        end = datetime.now().replace(hour=end_time.hour, minute=end_time.minute)
    # If no end given, show a 8 hour long graph
    else:
        end = (start + timedelta(hours=8))

    # If it's an update, only send the graph
    if 'update' in request.args and request.args['update']:
        return create_dashboard_gantt(graph_start=start,
                                      graph_end=end,
                                      machine_ids=machine_ids,
                                      title=graph_title,
                                      include_plotlyjs=False)
    else:
        graph = create_dashboard_gantt(graph_start=start,
                                       graph_end=end,
                                       machine_ids=machine_ids,
                                       title=graph_title,
                                       include_plotlyjs=True)

        return render_template("oee_displaying/dashboard.html",
                               update_interval_ms=update_interval_ms,
                               machine_group=machine_group,
                               graph=graph,
                               start=request.args['start'],
                               end=request.args['end'])

@bp.route('/sai-graph', methods=['GET', 'POST'])
def sai_graph():
    # Get a list of machines to provide a dropdown
    machines = Machine.query.all()

    machine_name_choices = [(str(m.id), m.name) for m in machines]
    # user_session = [ (str(ud.id), ud.time_login) for ud in UserSession.quary.all()]

    # Create the form
    form = JPQForm()
    form.key.choices = machine_name_choices
    # form.start_date.choice = user_session
    print(form.key.choices)

    # If the form has been submitted we need to create the graph
    if form.validate_on_submit():
        # Parse the machine we want from the form, and the start and end date of the graph
        machine_ids = [form.key.data]
        print(machine_ids)

        graph_start_date = form.start_date.data
        graph_end_date = form.end_date.data

        # Get a list of dates to use as X axis
        d = Settings.query.get(1).first_start
        print(d)
        dates = [d + timedelta(days=x) for x in range((graph_end_date - d).days + 1)]
        act_table = Activity.query.all()
        act_time = [(a.time_start,a.time_end) for a in act_table]




        if len(dates) == 0:
            return 0
        fig = go.Figure()
        # print('/n',fig)

        # Loop through the machines and get the OEE figure for each machine
        machine_ids.sort()
        print(machine_ids.sort())
        for machine_id in machine_ids:
            machine = Machine.query.get(machine_id)
            machine_oee_figures = []


            for t in dates:
                machine_oee_figures.append(get_daily_machine_oee(machine_id=machine_id, date=t))


            # group_ids.sort()
            # for group_id in group_ids:
            #   group = Machine.query.get(group_id)
            #  group_oee.append(get_daily_group_oee(group_id=group,date=d))

            # Add the trace to the graph

            fig.add_trace(go.Line(x=dates, y=machine_oee_figures, name=machine.name + ' OEE', opacity=0.5))

        # Modify the layout
        layout = Layout()
        layout.update({'title': 'OEE', 'height': 500, 'width': 800})
        layout.xaxis.update(range=[graph_start_date, graph_end_date])
        layout.xaxis.tickformat = '%a %d-%m-%Y'
        layout.xaxis.showgrid = True
        layout.xaxis.dtick = 86400000  # Space between ticks = 1 day
        # layout.yaxis.update(range=[0,24])
        fig.layout = layout
        print('\n', layout)

        # Plot the graph
        graph = plot(fig,
                     output_type="div",
                     include_plotlyjs=True,
                     config={"showLink": False})
        # print('\n',graph)
    else:
        graph = None

    return render_template("oee_displaying/sai_graph.html",
                           form=form,
                           graph=graph)


@bp.route('/sa-graph', methods=['GET', 'POST'])
def sa_graph():

    # Get a list of machines to provide a dropdown
    machines = Machine.query.all()

    machine_name_choices = [(str(m.id), m.name) for m in machines]
    #user_session = [ (str(ud.id), ud.time_login) for ud in UserSession.quary.all()]



    # Create the form
    form = JPQForm()
    form.key.choices = machine_name_choices
    #form.start_date.choice = user_session
    print(form.key.choices)


    # If the form has been submitted we need to create the graph
    if form.validate_on_submit():
        # Parse the machine we want from the form, and the start and end date of the graph
        machine_ids = [form.key.data]
        print(machine_ids)

        graph_start_date = form.start_date.data
        graph_end_date = form.end_date.data

        # Get a list of dates to use as X axis
        d = Settings.query.get(1).first_start
        print(d)
        dates = [(d -timedelta(hours=10, minutes=1,seconds=48))+ timedelta(days=x) for x in range((graph_end_date - d).days + 1)]
        print(dates)
        if len(dates) == 0:
            return 0
        fig = go.Figure()
       # print('/n',fig)


        # Loop through the machines and get the OEE figure for each machine
        machine_ids.sort()
        print(machine_ids.sort())
        for machine_id in machine_ids:
            machine = Machine.query.get(machine_id)
            machine_oee_figures = []
            machine_oee_availability = []
            machine_perfomance = []
            machine_quality =[]


            for t in dates:
                machine_oee_figures.append(get_daily_machine_oee(machine_id=machine_id, date=t))

                machine_oee_availability.append(get_machine_availability(machine_id=machine_id,
                                                                             time_start=t,
                                                                             time_end=t+timedelta(days=1)))



            jobs = Job.query \
                .filter(Job.end_time >= graph_start_date) \
                .filter(Job.start_time <= graph_end_date) \
                .filter(Job.machine_id == machine_id).all()
            for job in jobs:
                machine_perfomance.append(get_machine_performance(machine_id=machine_id,
                                                                  time_start=job.start_time,
                                                                  time_end=job.end_time))
                machine_quality.append(get_machine_quality(machine_id=machine_id,
                                                            time_start=job.start_time,
                                                            time_end=job.end_time))


            print(machine_oee_availability)

               # group_ids.sort()
                #for group_id in group_ids:
                 #   group = Machine.query.get(group_id)
                  #  group_oee.append(get_daily_group_oee(group_id=group,date=d))





            # Add the trace to the graph
            fig.add_trace(go.Scatter(x=dates, y=machine_perfomance, name=machine.name+'Performance',mode='markers+lines'))
            fig.add_trace(go.Line(x=dates, y=machine_quality, name=machine.name+' Quality'))
            #fig.add_trace(go.Scatter(x=dates, y=machine_oee_availability, name=machine.name, mode='markers'))
            fig.add_trace(go.Line(x=dates, y=machine_oee_availability, name=machine.name+' Availability', mode='lines'))
            #fig.add_trace(go.Line(x=dates, y=machine_oee_figures, name=machine.name+' OEE'))



        # Modify the layout
        layout = Layout()
        layout.update({'title':'OEE', 'height':500, 'width':1000})
        layout.xaxis.update(range=[graph_start_date, graph_end_date])
        layout.xaxis.tickformat = '%a %d-%m-%Y'
        layout.xaxis.showgrid = True
        layout.xaxis.dtick = 86400000  # Space between ticks = 1 day
        #layout.yaxis.update(range=[0,24])
        fig.layout = layout
        print('\n',layout)


        # Plot the graph
        graph = plot(fig,
                     output_type="div",
                     include_plotlyjs=True,
                     config={"showLink": False})
        #print('\n',graph)
    else:
        graph = None

    return render_template("oee_displaying/sa_graph.html",
                           form=form,
                           graph=graph)

@bp.route('/downtime-graph', methods=['GET', 'POST'])
def downtime_graph():
    machines = Machine.query.all()
    machine_name_choices = [("m_" + str(m.id), m.name) for m in machines]
    group_name_choices = [("g_" + str(mg.id), mg.name) for mg in MachineGroup.query.all()]
    machines_choices = [("all", "All Machines")] + \
                       [(MACHINES_CHOICES_HEADERS[0], MACHINES_CHOICES_HEADERS[0])] + group_name_choices + \
                       [(MACHINES_CHOICES_HEADERS[1], MACHINES_CHOICES_HEADERS[1])] + machine_name_choices
    form = DowntimeBarForm()
    form.key.choices = machines_choices
    if form.validate_on_submit():
        start = datetime.combine(date=form.start_date.data, time=form.start_time.data)
        end = datetime.combine(date=form.end_date.data, time=form.end_time.data)
        machine_ids = parse_requested_machine_list(form.key.data)
        total_activities_dict = None
        for machine_id in machine_ids:
            activities_dict = get_activity_duration_dict(requested_start=start,
                                                         requested_end=end,
                                                         machine_id=machine_id,
                                                         use_description_as_key=True,
                                                         units="minutes")

            if not total_activities_dict:
                # Use the first value to start the dict
                total_activities_dict = activities_dict
            else:
                for n in total_activities_dict:
                    total_activities_dict[n] += activities_dict[n]

        # Remove the "no user" code if requested:

        activity_code_names = list(total_activities_dict.keys())
        activity_code_durations = list(total_activities_dict.values())
        fig = go.Figure([go.Bar(x=activity_code_names, y=activity_code_durations)])
        fig.layout.title = "Total Time (Minutes)"
        graph = plot(fig,
                    output_type="div",
                    include_plotlyjs=True,
                    config={"showLink": False})
    else:
        graph = None

    return render_template("oee_displaying/downtime_graph.html",
                           form=form,
                           graph=graph)

@bp.route('/down-graph', methods=['GET', 'POST'])
def down_graph():
    machines = Machine.query.all()
    machine_name_choices = [("m_" + str(m.id), m.name) for m in machines]
    machine_names = [m.name for m in machines]
    print(machine_names)
    group_name_choices = [("g_" + str(mg.id), mg.name) for mg in MachineGroup.query.all()]
    machines_choices = [("all", "All Machines")] + \
                       [(MACHINES_CHOICES_HEADERS[0], MACHINES_CHOICES_HEADERS[0])] + group_name_choices + \
                       [(MACHINES_CHOICES_HEADERS[1], MACHINES_CHOICES_HEADERS[1])] + machine_name_choices
    form = DowntimeBarForm()
    form.key.choices = machines_choices
    if form.validate_on_submit():

        start = datetime.combine(date=form.start_date.data, time=form.start_time.data)
        end = datetime.combine(date=form.end_date.data, time=form.end_time.data)
        machine_ids = parse_requested_machine_list(form.key.data)


        labels = []
        values = []
        colours = []

        for machine_id in machine_ids:
           for ac in ActivityCode.query.all():

                   labels.append(ac.short_description)

                   values.append(calculate_activity_percent(machine_id, ac.id, start, end))

                   colours.append(ac.graph_colour)
                   layout = Layout(title=f"OEE for Machine", )

                   fig = {'data': [{'type': 'pie',
                                 'name': f"OEE for Machine",
                                 'labels': labels,
                                 'values': values,
                                 'direction': 'clockwise',
                                 'textposition': 'inside',
                                 'textinfo': 'label+percent',
                                 'marker': {'colors': colours}}],

                       'layout': layout}
                   graph = plot(fig,
                             output_type="div",
                             include_plotlyjs=True)

    else:
        graph = None

    return render_template("oee_displaying/down_graph.html",
                           form=form,
                           graph=graph)








