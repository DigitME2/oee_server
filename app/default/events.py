from datetime import datetime
from operator import attrgetter

from flask import current_app

from app.default.models import InputDevice, Activity, Machine, Job, ProductionQuantity, ActivityCode
from app.extensions import db
from app.login.models import UserSession, User
from config import Config

if Config.ENABLE_KAFKA:
    from app.kafka import events as kafka_events


def android_log_in(dt, user, input_device) -> bool:
    """ Start a new session. Usually called when a user logs in. Fails if no machine is assigned to the device"""

    if input_device.machine is None:
        current_app.logger.info(f"No machine assigned to {input_device}")
        return False
    input_device.machine.active_user_id = user.id
    input_device.active_user_id = user.id
    # Create the new user session
    new_us = UserSession(user_id=user.id,
                         input_device_id=input_device.id,
                         time_login=dt,
                         active=True)
    db.session.add(new_us)
    db.session.flush()  # To get the ID for the new user session
    db.session.refresh(new_us)
    input_device.active_user_session_id = new_us.id
    db.session.commit()
    # Change the machine activity now that the user is logged in
    change_activity(dt,
                    input_device.machine,
                    new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                    user_id=user.id)
    current_app.logger.info(f"Started user session {new_us}")
    if Config.ENABLE_KAFKA:
        kafka_events.android_login(user_name=user.username, station_name=input_device.machine.name)
    return True


def android_log_out(input_device: InputDevice, dt: datetime):
    current_app.logger.info(f"Logging out user_id:{input_device.active_user}")
    input_device.machine.active_user_id = -1
    user_name = input_device.active_user.username

    change_activity(dt,
                    input_device.machine,
                    new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                    user_id=-1)

    # End the user session
    input_device.active_user_session.time_logout = dt
    input_device.active_user_session.active = False

    input_device.active_user_session_id = None
    input_device.active_user_id = None
    db.session.commit()
    if Config.ENABLE_KAFKA:
        kafka_events.android_logout(user_name=user_name, machine_name=input_device.machine.name)


def change_activity(dt: datetime, machine: Machine, new_activity_code_id: int, user_id: int):
    new_activity_code = ActivityCode.query.get_or_404(new_activity_code_id)
    if not machine.active_job and \
            new_activity_code.machine_state in [Config.MACHINE_STATE_UPTIME, Config.MACHINE_STATE_OVERTIME]:
        raise UptimeWithoutJobError

    machine_state = new_activity_code.machine_state
    # If the activity is uptime during planned downtime, record it as overtime
    if machine.schedule_state == Config.MACHINE_STATE_PLANNED_DOWNTIME and \
            machine_state in [Config.MACHINE_STATE_UPTIME, Config.MACHINE_STATE_OVERTIME]:
        new_activity_code = ActivityCode.query.get(Config.MACHINE_STATE_OVERTIME)
        new_activity_code_id = new_activity_code.id

    # End the current activity
    if machine.current_activity:
        current_activity = machine.current_activity
        current_activity.end_time = dt

    # Start a new activity with no user
    new_activity = Activity(machine_id=machine.id,
                            start_time=dt,
                            activity_code_id=new_activity_code_id,
                            user_id=user_id)
    db.session.add(new_activity)
    db.session.flush()
    db.session.refresh(new_activity)
    machine.current_activity_id = new_activity.id
    current_app.logger.debug(f"Starting {new_activity} on {machine}")
    db.session.commit()
    if Config.ENABLE_KAFKA:
        kafka_events.set_machine_activity(new_activity_name=new_activity.activity_code.short_description,
                                          machine_name=machine.name,
                                          user_name=getattr(new_activity.user, "username", None))


def start_job(dt, machine: Machine, user_id: int, job_number, ideal_cycle_time_s) -> Job:
    # Create the job
    job = Job(start_time=dt,
              job_number=job_number,
              machine_id=machine.id,
              ideal_cycle_time_s=ideal_cycle_time_s,
              active=True)
    db.session.add(job)
    db.session.flush()
    db.session.refresh(job)
    machine.active_job_id = job.id
    starting_activity_code = machine.job_start_activity_id
    change_activity(dt,
                    machine,
                    new_activity_code_id=starting_activity_code,
                    user_id=user_id)
    db.session.commit()
    if Config.ENABLE_KAFKA:
        user = User.query.get(user_id)
        kafka_events.start_job(job_number=job_number,
                               user_name=user.username,
                               ideal_cycle_time_s=ideal_cycle_time_s)
    return job


def end_job(dt, job: Job, user_id):
    # Set the activity to down
    new_activity_code = Config.UNEXPLAINED_DOWNTIME_CODE_ID
    if job.machine.schedule_state == Config.MACHINE_STATE_PLANNED_DOWNTIME:
        new_activity_code = Config.CLOSED_CODE_ID
    # Don't create activities or set the active job if this job is being added retroactively
    job.machine.active_job_id = None
    change_activity(dt=dt,
                    machine=job.machine,
                    new_activity_code_id=new_activity_code,
                    user_id=user_id)
    job.end_time = dt
    job.active = False
    db.session.commit()
    if Config.ENABLE_KAFKA:
        user = User.query.get(user_id)
        kafka_events.end_job(job_number=job.job_number,
                             user_name=user.username)


def produced(time_end, quantity_good, quantity_rejects, job_id, machine_id, time_start=None):
    """ Record a production quantity. time_start and time_end mark the period of time in which the parts were created
    If time_start is not given, it is inferred from either the last ProductionQuantity or the start of the job"""
    # TODO Check there is uptime in the duration, or raise an exception
    if not time_start:
        job_production_quantities = ProductionQuantity.query.filter(ProductionQuantity.job_id == job_id).all()
        if len(job_production_quantities) > 0:
            last_pq = max(job_production_quantities, key=attrgetter('end_time'))
            time_start = last_pq.end_time
        else:
            job = Job.query.get(job_id)
            time_start = job.start_time

    production_quantity = ProductionQuantity(start_time=time_start,
                                             end_time=time_end,
                                             quantity_good=quantity_good,
                                             quantity_rejects=quantity_rejects,
                                             job_id=job_id,
                                             machine_id=machine_id)
    db.session.add(production_quantity)
    db.session.commit()


def start_shift(dt: datetime, machine):
    """ Run a shift change on a machine"""
    machine.schedule_state = Config.MACHINE_STATE_UPTIME
    db.session.commit()
    # If we're in the default "no shift" planned downtime activity (as expected)
    if machine.current_activity.activity_code_id == Config.CLOSED_CODE_ID:
        # Set to the standard unplanned downtime activity
        change_activity(dt, machine=machine, new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                        user_id=machine.active_user_id)
    # Otherwise we keep the same activity code and call change_activity to handle the change in machine_state
    else:
        change_activity(dt, machine=machine, new_activity_code_id=machine.current_activity.activity_code_id,
                        user_id=machine.active_user_id)


def end_shift(dt: datetime, machine):
    """ Run a shift change on a machine"""
    machine.schedule_state = Config.MACHINE_STATE_PLANNED_DOWNTIME
    db.session.commit()
    if not machine.active_job:
        # If the machine is in unplanned downtime (as expected)
        if machine.current_activity.activity_code.machine_state == Config.MACHINE_STATE_UNPLANNED_DOWNTIME:
            change_activity(dt, machine=machine, new_activity_code_id=Config.CLOSED_CODE_ID,
                            user_id=machine.active_user_id)
        # If machine is in planned downtime, make no change
    # If there's a job active keep the same activity
    else:
        # Call change activity if the machine is up so that it changes to overtime
        if machine.current_activity.activity_code.machine_state == Config.MACHINE_STATE_UPTIME:
            change_activity(dt, machine=machine, new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                            user_id=machine.active_user_id)
        # If machine is down during a job, make no change. The machine will be set to planned downtime on job end.


class UptimeWithoutJobError(Exception):
    pass
