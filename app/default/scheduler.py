from celery.schedules import crontab
from flask import current_app

from app.default.db_helpers import create_scheduled_activities
from app.extensions import celery_app
from app.oee_monitoring.machine_simulator import simulate_machines
from config import Config


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    current_app.logger.debug("Setting up periodic tests")
    sender.add_periodic_task(crontab(hour=3, minute=0),
                             daily_machine_schedule_task.s())
    if Config.DEMO_MODE:
        sender.add_periodic_task(10, simulate_machine_action_task.s())


@celery_app.task()
def daily_machine_schedule_task():
    current_app.logger.info("Running machine schedule celery task")
    create_scheduled_activities()
    return True


@celery_app.task()
def simulate_machine_action_task():
    current_app.logger.info("Running machine simulation celery task")
    simulate_machines()
