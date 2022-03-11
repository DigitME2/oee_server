from datetime import datetime

from app.default.db_helpers import get_machines_last_job
from config import Config


def get_machines_last_wo_number(machine_id):
    last_job = get_machines_last_job(machine_id)
    return last_job.wo_number


def time_autofill():
    return datetime.now().strftime("HH:mm")


REQUESTED_DATA_JOB_END = {"quantity_produced": {"title": "Quantity Produced",
                                                "type": "number",
                                                "autofill": ""},
                          "rejects": {"title": "Rejects",
                                      "type": "number",
                                      "autofill": ""}}
REQUESTED_DATA_JOB_START = {"wo_number": {"title": "Job Number",
                                          "type": "number",
                                          "autofill": ""},
                            "ideal_cycle_time": {"title": f"Ideal Cycle Time ({Config.IDEAL_CYCLE_TIME_UNITS[0]})",
                                                 "type": "number",
                                                 "autofill": ""},
                            "start_time": {"title": "Start Time",
                                           "type": "time",
                                           "autofill": "current"}}
