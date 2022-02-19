from app.default.db_helpers import get_machines_last_job
from config import Config

def get_machines_last_wo_number(machine_id):
    last_job = get_machines_last_job(machine_id)
    return last_job.wo_number


REQUESTED_DATA_JOB_END = {"quantity_produced": "Quantity Produced",
                          "rejects": "Rejects"}
REQUESTED_DATA_JOB_START = {"wo_number": "Job Number",
                            "ideal_cycle_time": f"Ideal Cycle Time ({Config.IDEAL_CYCLE_TIME_UNITS[0]})"}