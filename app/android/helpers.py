from app.default.db_helpers import get_machines_last_job
from config import Config


def has_been_set(machine_id):
    last_job = get_machines_last_job(machine_id)
    if last_job is None:
        return False
    for act in last_job.activities:
        if str(act.activity_code_id) != str(Config.SETTING_CODE_ID):
            return False
    return True


def get_machines_last_wo_number(machine_id):
    last_job = get_machines_last_job(machine_id)
    return last_job.wo_number
