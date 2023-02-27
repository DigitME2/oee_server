import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import redis
from apscheduler.schedulers.blocking import BlockingScheduler

from app import create_app
from app.default import events
from app.default.models import ShiftPeriod, SHIFT_STRFTIME_FORMAT
from config import Config

""" Scheduler to run scheduled tasks, to be run as a separate instance. To reload any changes, set redis key 
"schedule-modified" to 1. This scheduler checks for this key every minute and deletes it after reloading """

app = create_app()
logger = logging.getLogger('scheduler')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
Path('logs').mkdir(parents=True, exist_ok=True)
fh = RotatingFileHandler('logs/scheduler.log')
fh.setLevel(logging.INFO)
fh.setFormatter(logging.Formatter(style='{', fmt='{asctime} - {message}'))
logger.addHandler(fh)

aps_logger = logging.getLogger('apscheduler')
aps_logger.setLevel(logging.ERROR)

def add_all_jobs_to_scheduler(scheduler):
    scheduler.remove_all_jobs()
    add_shift_change_tasks(scheduler)
    scheduler.add_job(id="check-modification",
                      func=check_for_schedule_modification,
                      kwargs={"scheduler": scheduler},
                      trigger="cron",
                      day_of_week='*',
                      hour='*',
                      minute='*')


def add_shift_change_tasks(scheduler):
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


def check_for_schedule_modification(scheduler):
    with app.app_context():
        logger.debug("Checking for shift modification")
        r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)
        if r.exists("schedule-modified"):
            logger.info("Schedule modified. Reloading jobs...")
            add_all_jobs_to_scheduler(scheduler)
            r.delete("schedule-modified")


def shift_change(shift_period_id):
    with app.app_context():
        shift_period = ShiftPeriod.query.get(shift_period_id)
        now = datetime.now()
        shift_starting = (shift_period.shift_state == Config.MACHINE_STATE_UPTIME)
        logger.info(f"Shift {'starting' if shift_starting else 'ending'} ({shift_period})")
        for machine in shift_period.shift.machines:
            if shift_starting:
                events.start_shift(now, machine)
            else:
                events.end_shift(now, machine)


if __name__ == "__main__":
    with app.app_context():
        logger.info("Starting scheduler")
        s = BlockingScheduler()
        add_all_jobs_to_scheduler(s)
        s.start()
