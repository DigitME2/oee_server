from flask import jsonify
from flask_restful import Resource, reqparse
from app import rest_api, db
from app.default.models import ActivityCode, Activity, Machine


class ActivityAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('machine_number',
                                   type=str,
                                   required=True,
                                   help="No machine number provided",
                                   location='json')

        self.reqparse.add_argument('activity_code',
                                   required=True,
                                   help="No activity code provided",
                                   location='json')

        self.reqparse.add_argument('timestamp_start',
                                   required=True,
                                   help="No start time provided",
                                   location='json')

        self.reqparse.add_argument('timestamp_end',
                                   required=True,
                                   help="No end time provided",
                                   location='json')
        super(ActivityAPI, self).__init__()

    def post(self):
        args = self.reqparse.parse_args()
        machine_number = args['machine_number']
        machine = Machine.query.filter_by(machine_number=machine_number).first()
        code = args['activity_code']
        activity_code = ActivityCode.query.filter_by(activity_code=code).first()
        timestamp_start = args['timestamp_start']
        timestamp_end = args['timestamp_end']
        new_activity = Activity(activity_code_id=activity_code.id,
                                machine_id=machine.id,
                                timestamp_start=timestamp_start,
                                timestamp_end=timestamp_end)
        db.session.add(new_activity)
        db.session.commit()
        response = jsonify({"machine_number": machine.machine_number,
                         "activity_code": activity_code.activity_code,
                         "timestamp_start": new_activity.timestamp_start,
                         "timestamp_end": new_activity.timestamp_end})
        response.status_code = 201
        return response



rest_api.add_resource(ActivityAPI, '/machineactivity1')

