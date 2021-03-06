from datetime import datetime, timedelta, time

from flask import abort, request, render_template, current_app
from flask_login import login_required
from sqlalchemy import inspect

from app.extensions import db
from app.default.models import Machine, MachineGroup, Settings
from app.oee_displaying import bp
from app.oee_displaying.forms import MACHINES_CHOICES_HEADERS, state_gantt_chart, GanttForm, OeeLineForm, DowntimeBarForm, JobTableForm, \
    WOTableForm, RawDatabaseTableForm, ActivityDurationsTableForm
from app.oee_displaying.graphs import create_machine_gantt, create_multiple_machines_gantt, \
    create_dashboard_gantt, create_oee_line, create_downtime_bar
from app.oee_displaying.helpers import get_machine_status, parse_requested_machine_list
from app.oee_displaying.tables import get_work_order_table, get_job_table, get_raw_database_table, get_user_activity_table, get_machine_activity_table


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
    downtime_bar_form = DowntimeBarForm()
    downtime_bar_form.key.choices = machines_choices

    job_table_form = JobTableForm()
    wo_table_form = WOTableForm()
    activity_table_form = ActivityDurationsTableForm()
    raw_db_table_form = RawDatabaseTableForm()
    raw_db_table_form.key.choices = table_name_choices

    forms = [gantt_form, oee_line_form, downtime_bar_form, job_table_form, wo_table_form, activity_table_form, raw_db_table_form]

    # Check which form has been sent by the user
    form_sent = next((form for form in forms if form.__class__.__name__ == request.form.get('formType')), None)
    if isinstance(form_sent, GanttForm) and gantt_form.validate_on_submit():
        start = datetime.combine(date=gantt_form.start_date.data, time=gantt_form.start_time.data)
        end = datetime.combine(date=gantt_form.end_date.data, time=gantt_form.end_time.data)
        machine_ids = parse_requested_machine_list(gantt_form.key.data)
        if len(machine_ids) == 1:
            graph = create_machine_gantt(machine_id=machine_ids[0],
                                         graph_start=start.timestamp(),
                                         graph_end=end.timestamp())
        else:
            graph = create_multiple_machines_gantt(machine_ids=machine_ids,
                                                   graph_start=start.timestamp(),
                                                   graph_end=end.timestamp())

    elif isinstance(form_sent, OeeLineForm) and oee_line_form.validate_on_submit():
        graph = create_oee_line(graph_start_date=oee_line_form.start_date.data,
                                graph_end_date=oee_line_form.end_date.data)

    elif isinstance(form_sent, DowntimeBarForm) and downtime_bar_form.validate_on_submit():
        start = datetime.combine(date=downtime_bar_form.start_date.data, time=downtime_bar_form.start_time.data)
        end = datetime.combine(date=downtime_bar_form.end_date.data, time=downtime_bar_form.end_time.data)
        machine_ids = parse_requested_machine_list(downtime_bar_form.key.data)
        graph = create_downtime_bar(machine_ids=machine_ids,
                                    graph_start_timestamp=start.timestamp(),
                                    graph_end_timestamp=end.timestamp())

    elif isinstance(form_sent, JobTableForm) and job_table_form.validate_on_submit():
        graph = get_job_table(start_date=job_table_form.start_date.data,
                              end_date=job_table_form.end_date.data)

    elif isinstance(form_sent, WOTableForm) and wo_table_form.validate_on_submit():
        graph = get_work_order_table(start_date=wo_table_form.start_date.data,
                                     end_date=wo_table_form.end_date.data)

    elif isinstance(form_sent, ActivityDurationsTableForm) and activity_table_form.validate_on_submit():
        start = datetime.combine(date=downtime_bar_form.start_date.data, time=downtime_bar_form.start_time.data)
        end = datetime.combine(date=downtime_bar_form.end_date.data, time=downtime_bar_form.end_time.data)
        if "users" in activity_table_form.key.data:
            graph = get_user_activity_table(timestamp_start=start.timestamp(), timestamp_end=end.timestamp())
        elif "machines" in activity_table_form.key.data:
            graph = get_machine_activity_table(timestamp_start=start.timestamp(), timestamp_end=end.timestamp())
        else:
            graph = "Error"

    elif isinstance(form_sent, RawDatabaseTableForm) and raw_db_table_form.validate_on_submit():
        graph = get_raw_database_table(table_name=raw_db_table_form.key.data)


    else:
        graph = ""

    return render_template('oee_displaying/data.html',
                           machines=machines,
                           nav_bar_title="Graphs",
                           forms=forms,
                           graph=graph,
                           last_form=form_sent)


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

    graph_title = f"Machine group {machine_group.name}"

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

    if 'update' in request.args and request.args['update']:
        return create_dashboard_gantt(graph_start=start.timestamp(),
                                      graph_end=end.timestamp(),
                                      machine_ids=machine_ids,
                                      title=graph_title,
                                      include_plotlyjs=False)
    else:

        graph = create_dashboard_gantt(graph_start=start.timestamp(),
                                       graph_end=end.timestamp(),
                                       machine_ids=machine_ids,
                                       title=graph_title)
        return render_template("oee_displaying/dashboard.html",
                               update_interval_ms=update_interval_ms,
                               graph=graph,
                               start=request.args['start'],
                               end=request.args['end'])
