from datetime import datetime

from app.default import events
from app.default.models import ShiftPeriod, SHIFT_STRFTIME_FORMAT, Shift
from app.extensions import db, scheduler
from config import Config


def add_all_jobs_to_scheduler():
    scheduler.remove_all_jobs()
    add_shift_schedule_tasks()


def add_shift_schedule_tasks():
    shift_periods = ShiftPeriod.query.all()
    for period in shift_periods:
        job_id = f"shift_change for ShiftPeriod ID={period.id}"
        t = datetime.strptime(period.start_time, SHIFT_STRFTIME_FORMAT).time()
        scheduler.add_job(id=job_id,
                          func=shift_change,
                          kwargs={"shift_period_id": period.id},
                          trigger="cron",
                          day_of_week=period.day,
                          hour=t.hour,
                          minute=t.minute)


def shift_change(shift_period_id):
    with scheduler.app.app_context():
        shift_period = ShiftPeriod.query.get(shift_period_id)
        now = datetime.now()
        shift_starting = (shift_period.shift_state == Config.MACHINE_STATE_UPTIME)
        for machine in shift_period.shift.machines:
            if shift_starting:
                events.start_shift(now, machine)
            else:
                events.end_shift(now, machine)

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
