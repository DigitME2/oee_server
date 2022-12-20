from datetime import datetime

from app.default import events
from app.default.models import Machine, Shift
from app.extensions import db
from config import Config


def add_shift_schedule_tasks():
    shifts = Shift.query.all()


def start_shift(machine_id):
    machine = Machine.query.get(machine_id)
    machine.schedule_state = Config.MACHINE_STATE_RUNNING
    db.session.commit()
    if machine.current_activity == Config.UPTIME_CODE_ID:
        events.change_activity(datetime.now(),
                               machine,
                               Config.UPTIME_CODE_ID,
                               user_id=machine.active_user_id,
                               job_id=machine.active_job_id)


def end_shift():
    ...


# TODO End jobs that have obviously been left running overnight

#
# @celery_app.on_after_finalize.connect
# def setup_periodic_tasks(sender, **kwargs):
#     current_app.logger.info("Setting up periodic tests")
#     sender.add_periodic_task(crontab(hour=3, minute=0),
#                              daily_machine_schedule_task.s())
#     if Config.DEMO_MODE:
#         sender.add_periodic_task(Config.DATA_SIMULATION_FREQUENCY_SECONDS, simulate_machine_action_task.s())
#
#
# @celery_app.task()
# def daily_machine_schedule_task():
#     current_app.logger.info("Running machine schedule celery task")
#     create_all_scheduled_activities()
#     return True
#
#
# @celery_app.task()
# def daily_cleanup():
#     current_app.logger.info("Running daily cleanup")
#
#
#
# @celery_app.task()
# def simulate_machine_action_task():
#     from app.demo.machine_simulator import simulate_machines
#     current_app.logger.debug("Running machine simulation celery task")
#     simulate_machines()
