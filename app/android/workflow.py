import json
from datetime import datetime

import redis
from flask import current_app

from app.android.helpers import REQUESTED_DATA_JOB_END, get_job_start_data
from app.default.models import ActivityCode
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
        self.input_device = user_session.input_device
        self.machine = self.input_device.machine
        if not self.machine.active_job:
            self.state = "no_job"
        else:
            self.state = "active_job"
            self.job = self.machine.active_job
            self.current_activity = self.machine.current_activity
            self.activity_codes = self.get_activity_codes()
            self.current_activity_code = self.get_current_activity_code()

    def build_server_response(self):
        if self.state == "no_job":
            response = self.no_job_response()
        else:
            response = self.active_job_response()
        return response

    def no_job_response(self):
        input_type = self.machine.job_start_input_type
        input_autofill = self.machine.autofill_job_start_amount \
            if self.machine.autofill_job_start_input else ""
        return json.dumps({"workflow_type": self.workflow_type,
                           "state": self.state,
                           "machine_name": self.machine.name,
                           "user_name": self.user_session.user.username,
                           "requested_data": get_job_start_data(self.machine)})

    def active_job_response(self):
        # TODO Don't allow user to set overtime during planned production hours
        activity_codes_dicts = [{"activity_code_id": ac.id,
                                 "colour": ac.graph_colour,
                                 "description": ac.short_description}
                                for ac in self.activity_codes]
        return json.dumps({"machine_id": self.machine.id,
                           "workflow_type": self.workflow_type,
                           "state": self.state,
                           "job_number": self.job.job_number,
                           "current_activity_code_id": self.current_activity_code.id,
                           "current_machine_state": self.current_activity.activity_code.machine_state,
                           "activity_codes": activity_codes_dicts,
                           "colour": self.current_activity_code.graph_colour,
                           "requested_data_on_end": REQUESTED_DATA_JOB_END})

    def get_activity_codes(self):
        codes_to_show = ActivityCode.query.filter(ActivityCode.active).all()
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
        elif self.machine_state in [Config.MACHINE_STATE_UPTIME, Config.MACHINE_STATE_OVERTIME]:
            response = self.active_job_response()
        elif self.machine_state in [Config.MACHINE_STATE_UNPLANNED_DOWNTIME, Config.MACHINE_STATE_PLANNED_DOWNTIME]:
            self.state = "paused"
            response = self.active_job_response()
        else:
            current_app.logger.error(f"Invalid machine state: {self.machine_state}")
            raise Exception
        return response

    def get_machine_state(self):
        if hasattr(self, "current_activity"):
            return self.current_activity.activity_code.machine_state
        else:
            return Config.MACHINE_STATE_UNPLANNED_DOWNTIME


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
        # todo clarify total or good
        response["current_quantity"] = self.job.get_total_good_quantity()
        response["update_frequency"] = Config.RUNNING_TOTAL_UPDATE_FREQUENCY_SECONDS

        current_app.logger.debug(f"last update timestamp = {response['last_update']}")
        current_app.logger.debug(f"now = {datetime.now().timestamp()}")
        return json.dumps(response)


class Custom1Workflow(PausableWorkflow):

    def __init__(self, user_session: UserSession):
        super().__init__(user_session)
        self.workflow_type = "custom_1"

    def active_job_response(self):
        default_response = json.loads(super().active_job_response())
        response = default_response

        # Add parts specific to running total to the response
        if r.exists(f"job_{self.job.id}_last_update"):
            response["last_update"] = r.get(f"job_{self.job.id}_last_update")
        else:
            response["last_update"] = self.job.start_time.timestamp()
        # todo clarify total or good
        response["current_quantity"] = self.job.get_total_good_quantity()
        response["update_frequency"] = Config.RUNNING_TOTAL_UPDATE_FREQUENCY_SECONDS

        # Add parts specific to custom1 workflow
        if self.machine.id in Config.COMPONENTS:
            response["components"] = Config.COMPONENTS[self.machine.id]
        else:
            response["components"] = [""]

        response["categories"] = [{"category": c[0], "category_name": c[1]} for c in Config.DOWNTIME_CATEGORIES]

        # Send the category along with the activity codes

        response["activity_codes"] = [{"activity_code_id": ac.id,
                                       "colour": ac.graph_colour,
                                       "description": ac.short_description,
                                       "category": ac.downtime_category}
                                      for ac in self.activity_codes]
        current_app.logger.debug(f"last update timestamp = {response['last_update']}")
        current_app.logger.debug(f"now = {datetime.now().timestamp()}")
        return json.dumps(response)
