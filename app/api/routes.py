from app import db
from app.api import bp
from app.default.models import Machine, ActivityCode, Activity
from flask import request, jsonify
import json


@bp.route('/activity', methods=['POST'])
def machine_activity():
    """ Receives JSON data detailing a machine's activity and saves it to the database
    Example format:
    {
        "machine_number": 1,
        "activity_code": 1,
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
    if 'machine_number' not in data:
        response = jsonify({"error": "No machine_number provided"})
        response.status_code = 400
        return response
    machine_number = data['machine_number']
    machine = Machine.query.filter_by(machine_number=machine_number).first()

    if 'activity_code' not in data:
        response = jsonify({"error": "No activity_code provided"})
        response.status_code = 400
        return response
    code = data['activity_code']
    activity_code = ActivityCode.query.filter_by(activity_code=code).first()

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

    # Create and save the activity
    new_activity = Activity(activity_code_id=activity_code.id,
                            machine_id=machine.id,
                            timestamp_start=timestamp_start,
                            timestamp_end=timestamp_end)
    db.session.add(new_activity)
    db.session.commit()

    # Recreate the data and send it back to the client for confirmation
    response = jsonify({"machine_number": machine.machine_number,
                        "activity_code": activity_code.activity_code,
                        "timestamp_start": new_activity.timestamp_start,
                        "timestamp_end": new_activity.timestamp_end})
    response.status_code = 201
    return response
