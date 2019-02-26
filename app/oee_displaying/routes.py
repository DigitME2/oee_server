from app.oee_displaying.graph_helper import create_machine_gantt, create_all_machines_gantt
from app.oee_displaying import bp
from app.default.models import Machine
from datetime import datetime
from flask import abort, request, render_template
from flask_login import login_required





@bp.route('/machine')
@login_required
def machine_graph():
    """ The page showing the OEE of a machine and reasons for downtime"""
    try:
        machine_id = request.args.get('id')
    except TypeError:  # Thrown when parameter not in url
        abort(404)
        return
    machine = Machine.query.get_or_404(machine_id)

    try:
        # Get the values for the start and end time of the graph from the url
        start = int(request.args.get('start'))
        end = int(request.args.get('end'))
    except TypeError:  # Thrown when parameter not in url
        # todo handle this exception properly (test code)
        start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()  # = 1545728400.0
        end = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()  # = 1545757200.0

    graph = create_machine_gantt(graph_start=start, graph_end=end, machine=machine)
    nav_bar_title = "{machine_name} OEE | {start} - {end}".format(
        machine_name=machine.name,
        start=datetime.fromtimestamp(start).strftime("%a %d %b %Y (%H:%M"),
        end=datetime.fromtimestamp(end).strftime("%H:%M)"))
    return render_template('oee_displaying/machine.html',
                           graph=graph,
                           title=machine.name,
                           nav_bar_title=nav_bar_title)


@bp.route('/allmachines', methods=['GET', 'POST'])
@login_required
def all_machines_graph():
    """ The page showing the OEE of all the machines"""
    try:
        # Get the values for the start and end time of the graph from the url
        start = int(request.args.get('start'))
        end = int(request.args.get('end'))
    except TypeError: # Thrown when parameter not in url
        # todo handle this exception properly (test code)
        start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()  # = 1545728400.0
        end = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()  # = 1545757200.0

    graph = create_all_machines_gantt(graph_start=start, graph_end=end)
    return render_template('oee_displaying/allmachines.html', graph=graph)