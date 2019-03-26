from datetime import datetime
from random import randrange

from flask import render_template, request, jsonify, abort

from app import db
from app.testing import bp
from app.default.models import Machine, ActivityCode, Job, Activity, UPTIME_CODE_ID, UNEXPLAINED_DOWNTIME_CODE_ID
from app.login.models import User
from app.testing.forms import TestForm, NewBatchForm
from app.oee_displaying.graph_helper import create_machine_gantt
from plotly.offline import plot
from plotly.graph_objs import Layout
from datetime import datetime
from app.default.models import Activity, Machine, UPTIME_CODE_ID, UNEXPLAINED_DOWNTIME_CODE_ID, ActivityCode
import plotly.figure_factory as ff


@bp.route('/test')
def test():
    start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()
    end = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()
    machine = Machine.query.get(1)
    graph = create_machine_gantt(graph_start=start, graph_end=end, machine=machine)
    return render_template('testing/test.html', graph=graph)

def sort_activities(act):
    return act.activity_code.id


@bp.route('/updategraph', methods=['GET'])
def update_graph():
    try:
        machine_id = request.args.get('machine_id')
        if machine_id is None:
            raise TypeError
        # todo sometimes no id in args wasnt throwing the error and this solution isnt perfect
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
    return graph


@bp.route('/newbatch', methods=['GET', 'POST'])
def new_batch():
    """The page to create a new batch"""
    form = NewBatchForm()
    # Create list of part names to fill the part-type selection box
    part_names = [1, 2, 3]

    form.part_type.choices = part_names

    # Create a new batch, and new parts when form is submitted

    nav_bar_title = "Create new batch"
    return render_template('testing/newbatch.html', form=form,
                           nav_bar_title=nav_bar_title)


@bp.route('/createdata')
def create_data():
    """ Creates fake data to use for testing purposes"""
    db.create_all()

    unexplainedcode = ActivityCode(id=UNEXPLAINED_DOWNTIME_CODE_ID, code="EX", short_description='unexplained',
                                   graph_colour='rgb(178,34,34)')
    db.session.add(unexplainedcode)
    uptimecode = ActivityCode(id=UPTIME_CODE_ID, code="UP", short_description='uptime', graph_colour='rgb(0, 255, 128)')
    db.session.add(uptimecode)
    error1code = ActivityCode(id=2, code="ER1", short_description='error1', graph_colour='rgb(255,64,0)')
    db.session.add(error1code)
    error2code = ActivityCode(id=3, code="ER2", short_description='error2', graph_colour='rgb(255,0,0)')
    db.session.add(error2code)
    error3code = ActivityCode(id=4, code="ER3", short_description='error3', graph_colour='rgb(255,255,0)')
    db.session.add(error3code)
    db.session.commit()
    for i in range(0, 5):
        # noinspection PyArgumentList
        user = User(username="user"+str(i))
        user.set_password("password")

        new_machine = Machine(machine_number=str(i+1), name="Bridgeport " + str(i+1))
        db.session.add(new_machine)
        db.session.commit()

        job_start = datetime(year=2018, month=12, day=25, hour=9, minute=0)
        job_end = datetime(year=2018, month=12, day=25, hour=17, minute=0)
        new_job = Job(start_time=job_start.timestamp(),
                      end_time=job_end.timestamp(),
                      job_number=str(i),
                      machine_id=i,
                      user_id=i)

        db.session.add(new_job)
        db.session.commit()

        start = datetime(year=2018, month=12, day=25, hour=9, minute=0).timestamp()
        finish = datetime(year=2018, month=12, day=25, hour=17, minute=0).timestamp()
        time = start
        while time <= finish:
            uptime_activity = Activity(machine_id=i,
                                       timestamp_start=time,
                                       machine_state=1,
                                       activity_code_id=UPTIME_CODE_ID)
            time += randrange(600, 14400)
            uptime_activity.timestamp_end = time

            machine_state = randrange(0, 3)
            if machine_state == 1:
                machine_state = 0
            downtime_activity = Activity(machine_id=i,
                                         timestamp_start=time,
                                         machine_state=machine_state,
                                         activity_code_id=randrange(2, 5))
            time += randrange(60, 1200)
            downtime_activity.timestamp_end = time
            db.session.add(uptime_activity)
            db.session.add(downtime_activity)
            db.session.commit()

    return "Created fake data"
