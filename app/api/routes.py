import json
from datetime import datetime
from typing import Optional

import redis
import simple_websocket
from flask import request, jsonify, abort, make_response, current_app
from pydantic import BaseModel, validator

from app.api import bp
from app.default.db_helpers import complete_last_activity
from app.default.models import Machine, Activity
from app.extensions import db
from config import Config


class MachineStateChange(BaseModel):
    machine_id: int
    machine_state: int
    user_id: Optional[int]
    activity_code_id: Optional[int]


r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)


@bp.route('/api/machine-state-change', methods=['POST'])
def change_machine_state():
    """ Ends a machine's activity and starts a new one """
    post_data = MachineStateChange(**request.get_json())
    # Set the activity code id if it's not supplied
    if not post_data.activity_code_id:
        if post_data.machine_state == Config.MACHINE_STATE_RUNNING:
            activity_code_id = Config.UPTIME_CODE_ID
        else:
            activity_code_id = Config.UNEXPLAINED_DOWNTIME_CODE_ID
    else:
        activity_code_id = post_data.activity_code_id
    complete_last_activity(machine_id=post_data.machine_id)
    act = Activity(machine_id=post_data.machine_id,
                   activity_code_id=activity_code_id,
                   machine_state=post_data.machine_state,
                   time_start=datetime.now(),
                   user_id=post_data.user_id)

    db.session.add(act)
    db.session.commit()
    response = make_response("", 200)
    current_app.logger.info(f"Activity set to {act.activity_code_id}")
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
    # I was getting an issue with get_json() sometimes returning a string and sometimes dict so I did this
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
    first_message = ws.receive()
    first_message = json.loads(first_message)
    machine_id = first_message["machine_id"]
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
