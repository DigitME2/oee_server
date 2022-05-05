import json
from datetime import datetime

import redis
from flask import current_app, request

from app.android.helpers import REQUESTED_DATA_JOB_END, get_job_start_data
from app.default.db_helpers import get_current_machine_activity_id
from app.default.models import Job, Activity, ActivityCode
from app.login.models import UserSession
from config import Config

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)


class Workflow:
    workflow_type = "default"
    user_session = None
    machine = None
    state = None

    def __init__(self, user_session: UserSession):
        self.user_session = user_session
        self.machine = user_session.machine
        if not any(job.active for job in self.user_session.jobs):
            self.state = "no_job"
        else:
            self.state = "active_job"
            self.job = Job.query.filter_by(user_session_id=self.user_session.id, active=True).first()
            self.current_activity = Activity.query.get(get_current_machine_activity_id(self.machine.id))
            self.activity_codes = self.get_activity_codes()
            self.current_activity_code = self.get_current_activity_code()

    def build_server_response(self):
        if self.state == "no_job":
            response = self.no_job_response()
        else:
            response = self.active_job_response()
        return response

    def no_job_response(self):
        current_app.logger.debug(f"Returning state:no_job to {request.remote_addr}: no_job")
        input_type = self.user_session.machine.job_start_input_type
        input_autofill = self.user_session.machine.autofill_job_start_amount \
            if self.user_session.machine.autofill_job_start_input else ""
        return json.dumps({"workflow_type": self.workflow_type,
                           "state": self.state,
                           "requested_data": get_job_start_data(input_type=input_type,
                                                                input_autofill=input_autofill)})

    def active_job_response(self):
        current_app.logger.debug(f"Returning state: active_job to {request.remote_addr}: active_job")
        return json.dumps({"workflow_type": self.workflow_type,
                           "state": self.state,
                           "wo_number": self.job.wo_number,
                           "current_activity": self.current_activity_code.short_description,
                           "activity_codes": [code.short_description for code in self.activity_codes],
                           "colour": self.current_activity_code.graph_colour,
                           "requested_data_on_end": REQUESTED_DATA_JOB_END})

    def get_activity_codes(self):
        codes_to_show = ActivityCode.query.filter(ActivityCode.active,
                                                  ActivityCode.id != Config.NO_USER_CODE_ID).all()
        # Exclude excluded codes for the particular machine
        for code in codes_to_show:
            if code in self.machine.excluded_activity_codes:
                codes_to_show.pop(codes_to_show.index(code))
        return codes_to_show

    def get_current_activity_code(self):
        if self.current_activity:
            current_activity_code = self.current_activity.activity_code
        else:
            # If there's no activity, use unexplained downtime to stop crashes
            current_activity_code = ActivityCode.query.get(Config.UNEXPLAINED_DOWNTIME_CODE_ID)
        return current_activity_code


class DefaultWorkflow(Workflow):
    pass


class PausableWorkflow(Workflow):

    def __init__(self, user_session: UserSession):
        super().__init__(user_session)
        self.workflow_type = "pausable"
        self.machine_state = self.get_machine_state()

    def build_server_response(self):
        if self.state == "no_job":
            response = self.no_job_response()
        elif self.machine_state == Config.MACHINE_STATE_RUNNING:
            response = self.active_job_response()
        elif self.machine_state == Config.MACHINE_STATE_OFF:
            response = self.paused_job_response()
        else:
            current_app.logger.error(f"Invalid machine state: {self.machine_state}")
            raise Exception
        return response

    def active_job_response(self):
        current_app.logger.debug(f"Returning state: active_job to {request.remote_addr}: active_job")
        return json.dumps({"workflow_type": self.workflow_type,
                           "state": self.state,
                           "wo_number": self.job.wo_number,
                           "current_activity": self.current_activity_code.short_description,
                           "colour": self.current_activity_code.graph_colour,
                           "requested_data_on_end": REQUESTED_DATA_JOB_END})

    def paused_job_response(self):
        current_app.logger.debug(f"Returning state: paused to {request.remote_addr}: active_job")
        return json.dumps({"workflow_type": "pausable",
                           "state": "paused",
                           "activity_codes": [code.short_description for code in self.activity_codes],
                           "wo_number": self.job.wo_number,
                           "colour": self.current_activity_code.graph_colour})

    def get_machine_state(self):
        if hasattr(self, "current_activity"):
            return self.current_activity.machine_state
        else:
            return Config.MACHINE_STATE_OFF


class RunningTotalWorkflow(Workflow):

    def __init__(self, user_session: UserSession):
        super().__init__(user_session)
        self.workflow_type = "running_total"

    def active_job_response(self):
        default_response = json.loads(super().active_job_response())
        response = default_response

        if r.exists(f"job_{self.job.id}_last_update"):
            response["last_update"] = r.get(f"job_{self.job.id}_last_update")
        else:
            response["last_update"] = self.job.start_time.timestamp()
        response["current_quantity"] = self.job.quantity_produced
        response["update_frequency"] = Config.RUNNING_TOTAL_UPDATE_FREQUENCY_SECONDS

        current_app.logger.debug(f"last update timestamp = {response['last_update']}")
        current_app.logger.debug(f"now = {datetime.now().timestamp()}")
        return json.dumps(response)
