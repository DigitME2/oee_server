import json

from flask import current_app, request

from app.android.helpers import REQUESTED_DATA_JOB_END, get_job_start_data
from app.default.db_helpers import get_current_machine_activity_id
from app.default.models import Job, ActivityCode, Activity
from config import Config


def check_pausable_machine_state(user_session):
    # If there are no active jobs on the user session, send to new job screen
    machine = user_session.machine
    if not any(job.active for job in user_session.jobs):
        return json.dumps({"workflow_type": "pausable",
                           "state": "no_job",
                           "requested_data": get_job_start_data(input_type=user_session.machine.job_start_input_type)})

    # The current job is whatever job is currently active on the assigned machine
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    # Send the list of downtime reasons to populate a dropdown. Exclude up and no user
    selectable_codes = ActivityCode.query.filter(ActivityCode.active,
                                                 ActivityCode.id != Config.UPTIME_CODE_ID,
                                                 ActivityCode.id != Config.NO_USER_CODE_ID).all()
    # Get the current activity code to set the colour and dropdown
    try:
        current_activity = Activity.query.get(get_current_machine_activity_id(machine.id))
        current_activity_code = current_activity.activity_code
        current_machine_state = current_activity.machine_state
        colour = current_activity_code.graph_colour
    except TypeError:
        # This could be raised if there are no activities
        current_app.logger.error(f"Active job screen requested with no activities.")
        colour = "#ffffff"
        current_activity_code = ActivityCode.query.get(Config.UNEXPLAINED_DOWNTIME_CODE_ID)
        current_machine_state = Config.MACHINE_STATE_OFF

    # If the machine is paused (indicated by the machine_state), send to pause screen
    if current_machine_state == Config.MACHINE_STATE_OFF:
        return json.dumps({"workflow_type": "pausable",
                           "state": "paused",
                           "activity_codes": [code.short_description for code in selectable_codes],
                           "wo_number": current_job.wo_number,
                           "colour": colour})

    # Otherwise send to job in progress screen
    elif current_machine_state == Config.MACHINE_STATE_RUNNING:
        current_app.logger.debug(f"Returning state: active_job to {request.remote_addr}: active_job")
        return json.dumps({"workflow_type": "pausable",
                           "state": "active_job",
                           "wo_number": current_job.wo_number,
                           "current_activity": current_activity_code.short_description,
                           "colour": colour,
                           "requested_data_on_end": REQUESTED_DATA_JOB_END})
