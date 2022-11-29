import random
from datetime import datetime, timedelta
from random import randrange

from flask import current_app

from app.default import events
from app.default.db_helpers import machine_schedule_active
from app.default.models import Machine, Activity
from app.demo.models import DemoSettings
from app.extensions import db
from app.login.models import User, UserSession
from config import Config


def end_demo_job(job, simulation_datetime):
    current_app.logger.debug(f"ending job")
    job.end_time = simulation_datetime
    # Calculate a fake amount produced based on ideal amount produced multiplied by 80-100%
    quantity_produced = int(((job.end_time - job.start_time).seconds / job.ideal_cycle_time_s) *
                            (random.randrange(80, 100) / 100))
    quantity_rejects = int(job.quantity_produced * (random.random() / 4))
    events.end_job(simulation_datetime, job=job, quantity_produced=quantity_produced, quantity_rejects=quantity_rejects)


def start_demo_job(machine, user, simulation_datetime):
    """ Starts a new demo job. If no user session exists, starts one."""
    current_app.logger.debug(f"Starting new job")
    session = UserSession.query.filter_by(user_id=user.id, active=True).first()
    if session is None:
        session = UserSession(user_id=user.id,
                              input_device_id=user.id,
                              time_login=simulation_datetime,
                              active=True)
        db.session.add(session)
        db.session.commit()
    events.start_job(simulation_datetime, machine=machine,
                     user_id=user.id,
                     job_number=str(random.randint(1, 100000)),
                     ideal_cycle_time_s=10)


def change_demo_activity(machine, job, user, simulation_datetime):
    current_app.logger.debug(f"changing activity")
    chance_the_activity_is_uptime = 0.8
    if random.random() < chance_the_activity_is_uptime:
        new_activity_code_id = Config.UPTIME_CODE_ID
    else:
        # otherwise the activity is downtime
        new_activity_code_id = randrange(2, 7)
    events.change_activity(simulation_datetime,
                           machine,
                           new_activity_code_id=new_activity_code_id,
                           user_id=user.id,
                           job_id=job.id)


def simulate_machines(simulation_datetime: datetime = None):
    if not Config.DEMO_MODE:
        current_app.logger.warning("Fake data being created when app is not in DEMO_MODE")
    # Run for the current time if no datetime given
    if not simulation_datetime:
        simulation_datetime = datetime.now()
    for i in range(2, 9):  # Simulate the first 8 machines
        chance_to_skip_simulation = 0.90
        if random.random() < chance_to_skip_simulation:
            continue
        machine = Machine.query.get(i)
        user = User.query.get(i)
        if machine.id == 1:
            continue  # Don't simulate the first machine
        if not machine_schedule_active(machine, dt=simulation_datetime):
            # Don't run jobs if the machine is not scheduled to be running
            if machine.active_job:
                end_demo_job(machine.active_job, simulation_datetime)

        if machine.active_job:
            chance_to_end_job = 0.03
            if random.random() < chance_to_end_job:
                end_demo_job(machine.active_job, simulation_datetime)
            chance_to_change_activity = 0.2
            if random.random() < chance_to_change_activity:
                change_demo_activity(machine, machine.active_job, user, simulation_datetime)

        else:
            chance_to_start_job = 0.3
            if random.random() < chance_to_start_job:
                start_demo_job(machine, user, simulation_datetime)
        DemoSettings.query.get(1).last_machine_simulation = simulation_datetime
    db.session.commit()


def backfill_missed_simulations():
    current_app.logger.debug(f"Simulating activity to backfill missed dates "
                             f"at database address {Config.SQLALCHEMY_DATABASE_URI}")
    last_simulation = DemoSettings.query.get(1).last_machine_simulation
    # If the last simulation was too long ago, start from the requested days backfill
    if (datetime.now() - last_simulation) > timedelta(Config.DAYS_BACKFILL):
        simulation_start = datetime.now() - timedelta(Config.DAYS_BACKFILL)
    else:
        simulation_start = last_simulation
    # Create scheduled activities
    for i in dt_range(simulation_start, datetime.now(), Config.DATA_SIMULATION_FREQUENCY_SECONDS):
        simulate_machines(i)
    db.session.commit()


def dt_range(start_dt, end_dt, frequency_seconds):
    """ Returns a generator for a range of datetimes between the two dates, at the frequency specified """
    current_iteration = start_dt
    while current_iteration <= end_dt:
        current_iteration = current_iteration + timedelta(seconds=frequency_seconds)
        yield current_iteration


def get_dummy_machine_activity(time_start: datetime, time_end: datetime, job_id, machine_id):
    """ Creates fake activities for one machine between two times"""
    virtual_time = time_start
    activities = []
    while virtual_time <= time_end:
        uptime_activity = Activity(machine_id=machine_id,
                                   time_start=virtual_time,
                                   machine_state=Config.MACHINE_STATE_RUNNING,
                                   activity_code_id=Config.UPTIME_CODE_ID,
                                   job_id=job_id)
        virtual_time += randrange(400, 3000)
        uptime_activity.time_end = virtual_time
        activities.append(uptime_activity)

        downtime_activity = Activity(machine_id=machine_id,
                                     time_start=virtual_time,
                                     machine_state=Config.MACHINE_STATE_OFF,
                                     activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                                     job_id=job_id)
        virtual_time += randrange(60, 1000)
        downtime_activity.time_end = virtual_time
        activities.append(downtime_activity)

    return activities
