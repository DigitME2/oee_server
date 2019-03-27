from app.oee_displaying.graph_helper import create_machine_gantt, create_all_machines_gantt
from app.oee_displaying import bp
from app.default.models import Machine
from datetime import datetime, timedelta, time
from flask import abort, request, render_template
from flask_login import login_required


@bp.route('/graphs')
@login_required
def machine_graph():
    """ The page showing the OEE of a machine and reasons for downtime"""
    start_time = datetime.combine(datetime.today(), time.min)
    end_time = (start_time + timedelta(days=1))
    graph = create_all_machines_gantt(graph_start=start_time.timestamp(), graph_end=end_time.timestamp())
    nav_bar_title = "Machine Activity"
    return render_template('oee_displaying/machine.html',
                           machines=Machine.query.all(),
                           nav_bar_title=nav_bar_title,
                           graph=graph)


@bp.route('/allmachines', methods=['GET', 'POST'])
@login_required
def all_machines_graph():
    """ The page showing the OEE of all the machines"""
    try:
        # Get the values for the start and end time of the graph from the url
        start = int(request.args.get('start'))
        end = int(request.args.get('end'))
    except TypeError:  # Thrown when parameter not in url
        # todo handle this exception properly (test code)
        start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()  # = 1545728400.0
        end = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()  # = 1545757200.0

    graph = create_all_machines_gantt(graph_start=start, graph_end=end)
    return render_template('oee_displaying/allmachines.html',
                           graph=graph)


@bp.route('/updategraph', methods=['GET'])
def update_graph():

    # Get the date from the request and calculate the start and end time for the graph
    try:
        date_string = request.args.get('date')
        date = datetime.strptime(date_string, "%d-%m-%Y")
        # Get the values for the start and end time of the graph from the url
        start_time = date.timestamp()
        end_time = (date + timedelta(days=1)).timestamp()
    except TypeError:  # Thrown when parameter not in url
        # todo handle this exception properly (this is test code)
        start_time = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()  # = 1545728400.0
        end_time = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()  # = 1545757200.0

    # Get the machine id from the request
    try:
        machine_id = request.args.get('machine_id')
        if machine_id is None:
            raise TypeError
        # todo sometimes no id in args wasnt throwing the error and this solution isnt perfect

    # If id=-1 is passed, create a graph of all machines
        if int(machine_id) == -1:
            return create_all_machines_gantt(graph_start=start_time, graph_end=end_time)
        else:
            machine = Machine.query.get_or_404(machine_id)
            return create_machine_gantt(graph_start=start_time, graph_end=end_time, machine=machine)
    except TypeError:  # Thrown when parameter not in url
        abort(404)
        return
