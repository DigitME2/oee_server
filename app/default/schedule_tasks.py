from datetime import datetime

from app.default import events
from app.default.models import ShiftPeriod, SHIFT_STRFTIME_FORMAT, Shift
from app.extensions import db, scheduler


def add_shift_schedule_tasks():
    shift_periods = ShiftPeriod.query.all()
    for period in shift_periods:
        job_id = f"shift_change for ShiftPeriod ID={period.id}"
        t = datetime.strptime(period.start_time, SHIFT_STRFTIME_FORMAT).time()
        shift_id = period.shift_id
        scheduler.add_job(id=job_id,
                          func=lambda: shift_change(shift_id=shift_id, shift_state=period.shift_state),
                          trigger="cron",
                          day_of_week=period.day,
                          hour=t.hour,
                          minute=t.minute)


def shift_change(shift_id, shift_state):
    with scheduler.app.app_context():
        now = datetime.now()
        shift = Shift.query.get(shift_id)
        for machine in shift.machines:
            machine.schedule_state = shift_state
            db.session.commit()  # Commit here so that change_activity is aware of the new schedule state
            # Call change_activity, but keep the same activity code
            events.change_activity(now,
                                   machine=machine,
                                   new_activity_code_id=machine.current_activity_id,
                                   user_id=machine.active_user_id,
                                   job_id=machine.active_job_id)




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
