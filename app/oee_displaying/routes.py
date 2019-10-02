from app.oee_displaying.graph_helper import create_machine_gantt, create_multiple_machines_gantt, create_dashboard_gantt
from app.oee_displaying import bp
from app.default.models import Machine
from datetime import datetime, timedelta, time
from flask import abort, request, render_template, current_app
from flask_login import login_required

from app.oee_displaying.helpers import get_machine_status


@bp.route('/dashboard')
def dashboard():
    # Get the group of machines to show
    if 'machine_group' not in request.args:
        current_app.logger.warn(f"Request arguments {request.args} do not contain a machine_group")
        return abort(400, "No machine_group provided in url")
    machine_group = request.args['machine_group']
    machine_ids = list(machine.id for machine in Machine.query.filter_by(group=machine_group).all())

    graph_title = f"Machine group {machine_group}"

    start = datetime.combine(datetime.today(), time.min)
    end = (start + timedelta(days=1))

    if 'start' in request.args:
        start_time = datetime.strptime(request.args['start'], "%H:%M")
        start = start.replace(hour=start_time.hour, minute=start_time.minute)

    if 'end' in request.args:
        end_time = datetime.strptime(request.args['end'], "%H:%M")
        end = end.replace(hour=end_time.hour, minute=end_time.minute)

    graph = create_dashboard_gantt(graph_start=start.timestamp(),
                                   graph_end=end.timestamp(),
                                   machine_ids=machine_ids,
                                   title=graph_title)
    return render_template("oee_displaying/dashboard.html",
                           graph=graph)


@bp.route('/graphs')
@login_required
def multiple_machine_graph():
    """ The page showing the OEE of a machine and reasons for downtime"""
    start_time = datetime.combine(datetime.today(), time.min)
    end_time = (start_time + timedelta(days=1))
    graph = create_multiple_machines_gantt(graph_start=start_time.timestamp(),
                                           graph_end=end_time.timestamp(),
                                           machine_ids=(machine.id for machine in Machine.query.all()))
    nav_bar_title = "Machine Activity"
    current_app.logger.debug(f"Creating graph for all machines between {start_time} and {end_time}")
    return render_template('oee_displaying/machine.html',
                           machines=Machine.query.all(),
                           nav_bar_title=nav_bar_title,
                           graph=graph)

1568105560
@bp.route('/allmachinesstatus')
def all_machines_status():
    # Create a list of dictionaries containing the status for every machine
    machine_status_dicts = []
    for machine in Machine.query.all():
        machine_status_dicts.append(get_machine_status(machine.id))
    return render_template("oee_displaying/all_machines_status.html",
                           machine_status_dicts=machine_status_dicts)


@bp.route('/machinestatus/<machine_id>')
@login_required
def machine_status(machine_id):
    """ The page showing the OEE of a machine and reasons for downtime"""
    machine = Machine.query.get_or_404(machine_id)
    start_time = datetime.combine(datetime.today(), time.min)
    end_time = (start_time + timedelta(days=1))
    graph = create_machine_gantt(graph_start=start_time.timestamp(),
                                 graph_end=end_time.timestamp(),
                                 machine_id=machine.id)
    nav_bar_title = "Machine Activity"
    status_dict = get_machine_status(machine.id)
    return render_template('oee_displaying/machine_status.html',
                           machine_status_dict=status_dict,
                           nav_bar_title=nav_bar_title,
                           graph=graph)


@bp.route('/updategraph', methods=['GET'])
def update_graph():
    """ Called when new dates are requested for the graph"""

    # Get the date and machine from the url arguments
    if 'date' not in request.args:
        current_app.logger.warn(f"Request arguments {request.args} do not contain a date")
        return abort(400, "No date provided in url")
    if 'machine_id' not in request.args:
        current_app.logger.warn(f"Request arguments {request.args} do not contain a machine id")
        return abort(400, "No target machine provided in url")

    # Get the date from the request and calculate the start and end time for the graph
    date_string = request.args['date']
    try:
        date = datetime.strptime(date_string, "%d-%m-%Y")
    except ValueError:
        current_app.logger.warn("Error reading date for graph update", exc_info=True)
        return "Error reading date. Date must be in format DD-MM-YYYY"
    # Get the values for the start and end time of the graph from the url
    start_time = date.timestamp()
    end_time = (date + timedelta(days=1)).timestamp()

    machine_id = request.args['machine_id']
    # If id=-1 is passed, create a graph of all machines
    if int(machine_id) == -1:
        current_app.logger.debug(f"Creating graph for all machines between {start_time} and {end_time}")
        return create_multiple_machines_gantt(graph_start=start_time,
                                              graph_end=end_time,
                                              machine_ids=(machine.id for machine in Machine.query.all()))
    else:
        machine = Machine.query.get_or_404(machine_id)
        current_app.logger.debug(f"Creating graph for {machine} between {start_time} and {end_time}")
        return create_machine_gantt(graph_start=start_time, graph_end=end_time, machine_id=machine.id)
