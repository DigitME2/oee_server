import json

from flask import request, Response, abort, make_response

from app import db
from app.default.models import Machine, ActivityCode, Activity
from app.api import bp


@bp.route('/machineactivity', methods=['POST'])
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
    #TODO make this robust to bad requests

    if not request.is_json:
        abort()

    data = request.get_json()
    # I was getting an issue with get_json() sometimes returning a string and sometimes dict so I did this
    if isinstance(data, str):
        data = json.loads(data)

    if 'machine_number' not in data:
        return Response(status=400, )
    if 'activity_code' not in data:
        abort(404, )
    machine_number = data['machine_number']
    machine = Machine.query.filter_by(machine_number=machine_number).first()

    # Loop through the activities in the json body and add them to the database
    for a in data['activities']:
        code = a['activity_code']
        activity_code = ActivityCode.query.filter_by(activity_code=code).first()
        timestamp_start = a['timestamp_start']
        timestamp_end = a['timestamp_end']
        new_activity = Activity(activity_code_id=activity_code.id,
                                machine_id=machine.id,
                                timestamp_start=timestamp_start,
                                timestamp_end=timestamp_end)
        db.session.add(new_activity)
        db.session.commit()

    return Response(status=201)