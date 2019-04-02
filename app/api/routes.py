from app import db
from app.api import bp
from app.default.models import Machine, Activity, MACHINE_STATE_RUNNING, UPTIME_CODE_ID, UNEXPLAINED_DOWNTIME_CODE_ID
from flask import request, jsonify
import json
from time import time


def validate_timestamp(timestamp):
    """ Makes sure a given timestamp isn't too old and isn't in the future"""

    timeout = 604800
    future_buffer = 120

    if (time() - timeout) > timestamp > (time() + future_buffer):
        return False

    else:
        return True


@bp.route('/activity', methods=['POST'])
def machine_activity():
    """ Receives JSON data detailing a machine's activity and saves it to the database
    Assigns a simple activity code depending on machine state
    Example format:
    {
        "machine_id": 1,
        "machine_state": 1,
        "timestamp_start": 1500000000,
        "timestamp_end": 1500000000
    }
    """
    # Return an error if the request is not in json format
    if not request.is_json:
        response = jsonify({"error": "Request is not in json format"})
        response.status_code = 400
        return response

    data = request.get_json()
    # I was getting an issue with get_json() sometimes returning a string and sometimes dict so I did this
    if isinstance(data, str):
        data = json.loads(data)

    # Get all of the arguments, respond with an error if not provided
    if 'machine_id' not in data:
        response = jsonify({"error": "No machine_id provided"})
        response.status_code = 400
        return response
    machine = Machine.query.get_or_404(data['machine_id'])

    if 'machine_state' not in data:
        response = jsonify({"error": "No machine_state provided"})
        response.status_code = 400
        return response
    machine_state = data['machine_state']

    if 'timestamp_start' not in data:
        response = jsonify({"error": "No timestamp_start provided"})
        response.status_code = 400
        return response
    timestamp_start = data['timestamp_start']

    if 'timestamp_end' not in data:
        response = jsonify({"error": "No timestamp_end provided"})
        response.status_code = 400
        return response
    timestamp_end = data['timestamp_end']

    if not validate_timestamp(timestamp_start) or not validate_timestamp(timestamp_end):
        response = jsonify({"error": "Bad timestamp"})
        response.status_code = 400
        return response

    if machine_state == MACHINE_STATE_RUNNING:
        activity_id = UPTIME_CODE_ID
    else:
        activity_id = UNEXPLAINED_DOWNTIME_CODE_ID

    # Create and save the activity
    new_activity = Activity(machine_id=machine.id,
                            machine_state=machine_state,
                            activity_code_id=activity_id,
                            timestamp_start=timestamp_start,
                            timestamp_end=timestamp_end)
    db.session.add(new_activity)
    db.session.commit()

    # Recreate the data and send it back to the client for confirmation
    response = jsonify({"machine_id": machine.id,
                        "machine_state": new_activity.machine_state,
                        "timestamp_start": new_activity.timestamp_start,
                        "timestamp_end": new_activity.timestamp_end})
    response.status_code = 201
    return response


