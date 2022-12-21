import json
from datetime import datetime
from typing import Optional

import redis
import simple_websocket
from flask import request, jsonify, abort, make_response, current_app
from flask_login import current_user
from pydantic import BaseModel

from app.api import bp
from app.default import events
from app.default.forms import StartJobForm, EndJobForm
from app.default.models import Activity, ActivityCode, Machine, InputDevice, Job
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
                               "code": ac.code,
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
    events.change_activity(datetime.now(),
                           machine=machine,
                           new_activity_code_id=activity_code_id,
                           user_id=post_data.user_id,
                           job_id=machine.active_job_id)
    response = make_response("", 200)
    current_app.logger.debug(f"Activity set to id {activity_code_id}")
    return response


@bp.route('/api/activity/<activity_id>', methods=['PUT'])
def edit_activity(activity_id):
    """ Edit an activity without ending it"""
    activity = Activity.query.get_or_404(activity_id)
    if not request.is_json:
        response = jsonify({"error": "Request is not in json format"})
        response.status_code = 400
        return response

    data = request.get_json()
    # I was getting an issue with get_json() sometimes returning a string and sometimes dict, so I did this
    if isinstance(data, str):
        data = json.loads(data)

    if "activity_code_id" in data:
        activity.activity_code_id = data["activity_code_id"]
        db.session.commit()
        response = jsonify({"message": "Success"})
        response.status_code = 200
        return response
    else:
        abort(400)


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
    end_job_form = EndJobForm()
    if end_job_form.validate_on_submit():
        job_id = request.form.get("job_id")
        job = Job.query.get_or_404(job_id)
        # Remove it as active_job from its machine
        machine = Machine.query.filter(Machine.active_job_id == job.id).first()
        machine.active_job_id = None
        db.session.commit()
        events.produced(now,
                        quantity_good=end_job_form.quantity_good.data,
                        quantity_rejects=end_job_form.rejects.data,
                        job_id=job.id,
                        machine_id=machine.id)
        events.end_job(now, job=job)
    return make_response("", 200)
