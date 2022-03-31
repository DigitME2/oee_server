import json

from flask import current_app, request

from app.android.helpers import REQUESTED_DATA_JOB_END, get_job_start_data
from app.default.db_helpers import get_current_machine_activity_id
from app.default.models import Job, ActivityCode, Activity
from config import Config


def check_default_machine_state(user_session):
    """ Checks for, and returns, the state for a machine that follows the default workflow"""
    # If there are no active jobs on the user session, send to new job screen
    if not any(job.active for job in user_session.jobs):
        current_app.logger.debug(f"Returning state:no_job to {request.remote_addr}: no_job")
        input_type = user_session.machine.job_start_input_type
        input_autofill = user_session.machine.autofill_job_start_amount \
            if user_session.machine.autofill_job_start_input else ""
        return json.dumps({"workflow_type": "default",
                           "state": "no_job",
                           "requested_data": get_job_start_data(input_type=input_type,
                                                                input_autofill=input_autofill)})

    # The current job is whatever job is currently active on the assigned machine
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Send the list of downtime reasons to populate a dropdown. Exclude no user
    all_active_codes = ActivityCode.query.filter(ActivityCode.active,
                                                 ActivityCode.id != Config.NO_USER_CODE_ID).all()
    # Get the current activity code to set the colour and dropdown
    try:
        machine = user_session.machine
        current_activity = Activity.query.get(get_current_machine_activity_id(machine.id))
        current_activity_code = current_activity.activity_code
        colour = current_activity_code.graph_colour
    except TypeError:
        # This could be raised if there are no activities
        current_app.logger.error(f"Active job screen requested with no activities.")
        colour = "#c9b3b3"
        current_activity_code = ActivityCode.query.get(Config.UNEXPLAINED_DOWNTIME_CODE_ID)

    current_app.logger.debug(f"Returning state: active_job to {request.remote_addr}: active_job")
    return json.dumps({"workflow_type": "default",
                       "state": "active_job",
                       "wo_number": current_job.wo_number,
                       "current_activity": current_activity_code.short_description,
                       "activity_codes": [code.short_description for code in all_active_codes],
                       "colour": colour,
                       "requested_data_on_end": REQUESTED_DATA_JOB_END})
