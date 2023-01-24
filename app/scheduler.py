from datetime import datetime

from celery.schedules import crontab
from flask import current_app

from app.default import events
from app.default.models import ShiftPeriod, SHIFT_STRFTIME_FORMAT
from app.extensions import celery_app
from config import Config


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    current_app.logger.info("Setting up periodic tests")
    add_shift_schedule_tasks()
    if Config.DEMO_MODE:
        sender.add_periodic_task(Config.DATA_SIMULATION_FREQUENCY_SECONDS, simulate_machine_action_task.s())


def add_shift_schedule_tasks():
    shift_periods = ShiftPeriod.query.all()
    current_app.logger.info("Setting up celery shift tasks")
    for period in shift_periods:
        task_name = f"shift-change-period-{period.id}"
        t = datetime.strptime(period.start_time, SHIFT_STRFTIME_FORMAT).time()
        day_number = {"mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6, "sun": 0}[period.day]
        celery_app.add_periodic_task(crontab(hour=t.hour, minute=t.minute, day_of_week=day_number),
                                     shift_change.s(period.id),
                                     name=task_name)


@celery_app.task
def shift_change(shift_period_id):
    current_app.logger.debug(f"Running shift change for period {shift_period_id}")
    shift_period = ShiftPeriod.query.get(shift_period_id)
    now = datetime.now()
    shift_starting = (shift_period.shift_state == Config.MACHINE_STATE_UPTIME)
    for machine in shift_period.shift.machines:
        if shift_starting:
            events.start_shift(now, machine)
        else:
            events.end_shift(now, machine)


@celery_app.task()
def daily_cleanup():
    current_app.logger.info("Running daily cleanup")


@celery_app.task()
def simulate_machine_action_task():
    from app.demo.machine_simulator import simulate_machines
    current_app.logger.debug("Running machine simulation celery task")
    simulate_machines()
