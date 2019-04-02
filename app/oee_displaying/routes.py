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


@bp.route('/updategraph', methods=['GET'])
def update_graph():

    # Get the date and machine from the url arguments
    if 'date' not in request.args:
        return abort(400, "No date provided in url")
    if 'machine_id' not in request.args:
        return abort(400, "No target machine provided in url")

    # Get the date from the request and calculate the start and end time for the graph
    date_string = request.args['date']
    date = datetime.strptime(date_string, "%d-%m-%Y")
    # Get the values for the start and end time of the graph from the url
    start_time = date.timestamp()
    end_time = (date + timedelta(days=1)).timestamp()

    machine_id = request.args['machine_id']
    # If id=-1 is passed, create a graph of all machines
    if int(machine_id) == -1:
        return create_all_machines_gantt(graph_start=start_time, graph_end=end_time)
    else:
        machine = Machine.query.get_or_404(machine_id)
        return create_machine_gantt(graph_start=start_time, graph_end=end_time, machine=machine)

