import json
from datetime import datetime
from typing import Optional

import redis
import simple_websocket
from flask import request, jsonify, abort, make_response, current_app, Response
from flask_login import current_user
from pydantic import BaseModel

import app.default.edit_events
from app.api import bp
from app.default import events, edit_events
from app.default.events import UptimeWithoutJobError
from app.default.forms import StartJobForm, RecordProductionForm, EditActivityForm, FullJobForm, \
    RecordPastProductionForm, ModifyProductionForm
from app.default.models import Activity, ActivityCode, Machine, InputDevice, Job, ProductionQuantity
from app.extensions import db
from app.login.models import User
from config import Config


class MachineStateChange(BaseModel):
    machine_id: int
    user_id: Optional[int]
    machine_state: Optional[int]
    activity_code_id: Optional[int]


r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)


@bp.route('/api/users')
def get_users():
    users = []
    for user in User.query.all():
        users.append({"username": user.username, "user_id": user.id, "admin": user.admin})
    return jsonify(users)


@bp.route('/api/activity-codes')
def get_activity_codes():
    activity_codes = []
    for ac in ActivityCode.query.all():
        activity_codes.append({"short_description": ac.short_description,
                               "id": ac.id,
                               "graph_colour": ac.graph_colour,
                               "long_description": ac.long_description})
    return jsonify(activity_codes)


@bp.route('/api/machine-state-change', methods=['POST'])
def change_machine_state():
    """ Ends a machine's activity and starts a new one """
    post_data = MachineStateChange(**request.get_json())
    # If only the state is supplied (up/down), create the activity code id
    if post_data.machine_state and not post_data.activity_code_id:
        if post_data.machine_state == Config.MACHINE_STATE_UPTIME:
            activity_code_id = Config.UPTIME_CODE_ID
        else:
            activity_code_id = Config.UNEXPLAINED_DOWNTIME_CODE_ID
    else:
        activity_code_id = post_data.activity_code_id
    machine = Machine.query.get_or_404(post_data.machine_id)
    if activity_code_id == Config.UPTIME_CODE_ID and not machine.active_job:
        return abort(400)
    events.change_activity(datetime.now(),
                           machine=machine,
                           new_activity_code_id=activity_code_id,
                           user_id=post_data.user_id)
    response = make_response("", 200)
    current_app.logger.debug(f"Activity set to id {activity_code_id}")
    return response


@bp.route('/api/activity/<activity_id>', methods=['PUT'])
def edit_activity(activity_id=None):
    """ Edit an activity without ending it"""
    now = datetime.now()
    form = EditActivityForm()
    new_activity = Activity.query.get_or_404(activity_id)
    if form.validate_on_submit():
        new_start = datetime.combine(form.start_date.data, form.start_time.data)
        new_end = datetime.combine(form.end_date.data, form.end_time.data)
        if new_start > new_end:
            return abort(Response(status=400, response="End time before start time"))
        new_activity_code_id = form.activity_code.data
        new_activity_code = ActivityCode.query.get_or_404(new_activity_code_id)
        try:
            edit_events.modify_activity(modified_act=new_activity, new_start=new_start, new_end=new_end,
                                        new_activity_code=new_activity_code)
        except UptimeWithoutJobError:
            return make_response("Cannot set to uptime when no job is active", 400)

        response = jsonify({"message": "Success"})
        response.status_code = 200
        return response
    else:
        return abort(400)


@bp.route('/api/new-activity', methods=['POST'])
def create_past_activity(activity_id=None):
    """ Create an activity in the past """
    now = datetime.now()
    form = EditActivityForm()
    if form.validate_on_submit():
        start = datetime.combine(form.start_date.data, form.start_time.data)
        end = datetime.combine(form.end_date.data, form.end_time.data)
        machine_id = request.form.get("machine_id")  # Hidden input
        activity_code = ActivityCode.query.get(form.activity_code.data)
        try:
            edit_events.add_past_activity(start_time=start, end_time=end, activity_code_id=activity_code.id,
                                          machine_id=machine_id)
        except UptimeWithoutJobError:
            return make_response("Cannot set to uptime when no job is active", 400)
        response = jsonify({"message": "Success"})
        response.status_code = 200
        return response
    else:
        return abort(400)


@bp.route('/api/activity-updates', websocket=True)
def activity_updates():
    """ Receive updates on the activity changes for a machine. The first message sent by the client should be the
    ID of the machine to be monitored. The server will then send the activity code ID every time it changes """
    ws = simple_websocket.Server(request.environ)
    p = r.pubsub()
    # Wait for the client to send which machine to monitor
    first_message = ws.receive()
    first_message = json.loads(first_message)
    machine_id = first_message["machine_id"]
    # Send the client the current activity code
    machine = Machine.query.get_or_404(machine_id)
    ws.send(machine.current_activity.activity_code_id)
    p.subscribe("machine" + str(machine_id) + "activity")
    current_app.logger.info(f"Machine ID {machine_id} websocket connected")
    try:
        while True:
            for response in p.listen():
                if response["type"] == "message":
                    ws.send(response["data"])
    except simple_websocket.ConnectionClosed:
        pass
    return ''


@bp.route('/api/input-device-updates', websocket=True)
def input_device_updates():
    """ Connected to by an input device to receive updates such as activity changes/ job start/ logout.
    The first message sent by the client should be the input device's UUID. """
    ws = simple_websocket.Server(request.environ)
    p = r.pubsub()
    # Wait for the client to send which machine to monitor
    first_message = ws.receive()
    first_message = json.loads(first_message)
    uuid = first_message["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=uuid).first()
    # Send the client the current activity code
    ws.send(input_device.machine.current_activity.activity_code_id)
    machine_activity_channel = "machine" + str(1) + "activity"
    input_device_channel = "input_device" + str(1)
    p.subscribe(machine_activity_channel)
    p.subscribe(input_device_channel)
    current_app.logger.debug(f"Device {input_device.name} websocket connected")
    try:
        while True:
            for response in p.listen():
                if response["type"] == "message":
                    if response["channel"] == machine_activity_channel:
                        ws.send({"action": "activity_change",
                                 "activity_code_id": response["data"]})
                    elif response["channel"] == input_device_channel:
                        if response["data"] == "logout":
                            ws.send({"action": "logout"})
    except simple_websocket.ConnectionClosed:
        pass
        current_app.logger.debug(f"Device {input_device.name} websocket disconnected")
    return ''


@bp.route('/api/force-logout/<input_device_id>', methods=["POST"])
def force_android_logout(input_device_id):
    """ Log out a user from an android tablet remotely. """
    input_device = InputDevice.query.get_or_404(input_device_id)
    events.android_log_out(input_device, datetime.now())
    # Publish to Redis to inform clients
    r.publish("input_device" + str(input_device_id), "logout")

    return make_response("", 200)


@bp.route('/api/start-job', methods=["POST"])
def start_job():
    """ Start a job on a machine. """
    now = datetime.now()
    start_job_form = StartJobForm()
    if start_job_form.validate_on_submit():
        machine_id = request.form.get("machine_id")
        machine = Machine.query.get(machine_id)
        if not machine:
            return abort(400)
        events.start_job(now,
                         machine=machine,
                         user_id=current_user.id,
                         job_number=start_job_form.job_number.data,
                         ideal_cycle_time_s=start_job_form.ideal_cycle_time.data)
    return make_response("", 200)


@bp.route('/api/end-job', methods=["POST"])
def end_job():
    """ End a job"""
    now = datetime.now()
    end_job_form = RecordProductionForm()
    if end_job_form.validate_on_submit():
        job_id = request.form.get("job_id")
        job = Job.query.get_or_404(job_id)
        machine = job.machine
        db.session.commit()
        events.produced(now,
                        quantity_good=end_job_form.quantity_good.data,
                        quantity_rejects=end_job_form.quantity_rejects.data,
                        job_id=job.id,
                        machine_id=machine.id)
        events.end_job(now, job=job, user_id=current_user.id)
    return make_response("", 200)


@bp.route('/api/edit-past-job', methods=["POST"])
def edit_past_job():
    now = datetime.now()
    form = FullJobForm()
    job_id = request.form.get("job_id")
    job = Job.query.get(job_id)
    quantity_good = form.quantity_good.data
    quantity_rejects = form.quantity_rejects.data
    if not quantity_good:
        quantity_good = 0
    if not quantity_rejects:
        quantity_rejects = 0
    if not job:
        return abort(400)
    new_start = datetime.combine(form.start_date.data, form.start_time.data)
    if job.active:
        new_end = None
    else:
        if not form.end_date.data or not form.end_time.data:
            return abort(400)
        else:
            new_end = datetime.combine(form.end_date.data, form.end_time.data)
            if new_start > new_end:
                return abort(Response(status=400, response="End time before start time"))
    try:
        app.default.edit_events.modify_job(job=job, new_start=new_start, new_end=new_end,
                                           ideal_cycle_time=form.ideal_cycle_time.data,
                                           quantity_good=quantity_good,
                                           quantity_rejects=quantity_rejects,
                                           job_number=form.job_number.data)

    except app.default.edit_events.OverlappingJobsError:
        return make_response("Cannot have two jobs on a machine at once", 400)
    except app.default.edit_events.IntegrityError:
        return make_response("Cannot edit job quantity because there are multiple production records for this job."
                             " Edit in the production table", 400)
    except NotImplementedError:
        return make_response("Cannot edit a job with multiple production quantity records yet", 500)

    response = jsonify({"message": "Success"})
    response.status_code = 200
    return response


@bp.route('/api/new-past-job', methods=["POST"])
def add_past_job():
    """ Insert a job in the past """
    form = FullJobForm()
    if form.validate_on_submit():
        machine_id = request.form.get("machine_id")
        machine = Machine.query.get(machine_id)
        if not machine:
            return abort(400)
        start = datetime.combine(form.start_date.data, form.start_time.data)
        end = datetime.combine(form.end_date.data, form.end_time.data)
        try:
            edit_events.add_past_job(start, end,
                                     machine=machine,
                                     ideal_cycle_time=form.ideal_cycle_time.data,
                                     job_number=form.job_number.data,
                                     quantity_good=form.quantity_good.data,
                                     quantity_rejects=form.quantity_rejects.data)
            return make_response("", 200)
        except app.default.edit_events.OverlappingJobsError:
            return make_response("Cannot have two jobs on a machine at once", 400)
    else:
        return make_response("Error in form", 400)


@bp.route('/api/production', methods=['POST'])
def record_production():
    """ Update the production amount on a live job"""
    now = datetime.now()
    form = RecordProductionForm()
    if form.validate_on_submit():
        job_id = request.form.get("job_id")
        job = Job.query.get(job_id)
        machine = job.machine
        db.session.commit()
        events.produced(now,
                        quantity_good=form.quantity_good.data,
                        quantity_rejects=form.quantity_rejects.data,
                        job_id=job.id,
                        machine_id=machine.id)
        return make_response("", 200)
    else:
        return make_response("Form error", 400)


@bp.route('/api/past-production', methods=['POST'])
def record_past_production():
    """ Record an amount of production that occurred in the past"""
    form = RecordPastProductionForm()
    form.job.choices = [(j.id, j.job_number) for j in Job.query.all()]  # Not strictly correct but not worth validation
    if form.validate_on_submit():
        job = Job.query.get(form.job.data)
        start = datetime.combine(form.start_date.data, form.start_time.data)
        end = datetime.combine(form.end_date.data, form.end_time.data)
        edit_events.add_past_production_record(time_start=start,
                                               time_end=end,
                                               quantity_good=form.quantity_good.data,
                                               quantity_rejects=form.quantity_rejects.data,
                                               job_id=job.id,
                                               machine_id=job.machine_id)
        return make_response("", 200)
    else:
        return make_response("Form error", 400)


@bp.route('/api/production/<production_quantity_id>', methods=['PUT'])
def edit_production(production_quantity_id):
    """ Edit an existing production record"""
    form = ModifyProductionForm()
    production_quantity = ProductionQuantity.query.get_or_404(production_quantity_id)
    if form.validate_on_submit():
        start = datetime.combine(form.start_date.data, form.start_time.data)
        end = datetime.combine(form.end_date.data, form.end_time.data)
        edit_events.modify_production_record(record=production_quantity,
                                             time_start=start,
                                             time_end=end,
                                             quantity_good=form.quantity_good.data,
                                             quantity_rejects=form.quantity_rejects.data)
        return make_response("", 200)
    else:
        return make_response("Form error", 400)


# TODO Allow deleting production record
# TODO Allow deleting uptime
