from datetime import datetime
from operator import attrgetter
from typing import Optional

from flask import current_app

from app.extensions import db
from app.default.models import InputDevice, Activity, Machine, Job, ProductionQuantity
from app.login.models import UserSession
from config import Config


def android_log_in(dt, user, input_device) -> bool:
    """ Start a new session. Usually called when a user logs in. Fails if no machine is assigned to the device"""

    if input_device.machine is None:
        current_app.logger.info(f"No machine assigned to {input_device}")
        return False
    input_device.machine.active_user_id = user.id
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
                    user_id=user.id,
                    job_id=input_device.machine.active_job_id)
    current_app.logger.info(f"Started user session {new_us}")
    return True


def android_log_out(input_device: InputDevice, dt: datetime):
    current_app.logger.info(f"Logging out user_id:{input_device.active_user}")
    input_device.machine.active_user_id = -1

    change_activity(dt,
                    input_device.machine,
                    new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                    user_id=-1,
                    job_id=input_device.machine.active_job_id)

    # End the user session
    input_device.active_user_session.time_logout = dt
    input_device.active_user_session.active = False

    input_device.active_user_session_id = None
    input_device.active_user_id = None
    db.session.commit()


# TODO Modify to use the machine state directly from the activity code instead of inferring it
#  Make sure to respect whether it's planned or unplanned depending on the scheduled state
#  Consider having different activity codes for planned and unplanned downtime
def change_activity(dt: datetime, machine: Machine, new_activity_code_id: int, user_id: int, job_id: Optional[int]):
    # Calculate the machine state based on the scheduled state and the activity code given
    if machine.schedule_state == Config.MACHINE_STATE_UPTIME:
        if new_activity_code_id == Config.UPTIME_CODE_ID:
            # Machine is running while scheduled to run
            machine_state = Config.MACHINE_STATE_UPTIME
        else:
            # Machine is down while scheduled to run
            machine_state = Config.MACHINE_STATE_UNPLANNED_DOWNTIME
    elif machine.schedule_state == Config.MACHINE_STATE_PLANNED_DOWNTIME:
        if new_activity_code_id == Config.UPTIME_CODE_ID:
            # Machine is running while in planned downtime
            machine_state = Config.MACHINE_STATE_OVERTIME
        else:
            # Machine is down in planned downtime
            machine_state = Config.MACHINE_STATE_PLANNED_DOWNTIME
    else:
        current_app.logger.warning(f"Incorrect scheduled state for {machine}")
        machine_state = -1

    # End the current activity
    if machine.current_activity:
        current_activity = machine.current_activity
        current_activity.end_time = dt

    # Start a new activity with no user
    new_activity = Activity(machine_id=machine.id,
                            start_time=dt,
                            activity_code_id=new_activity_code_id,
                            machine_state=machine_state,
                            user_id=user_id,
                            job_id=job_id)
    db.session.add(new_activity)
    db.session.flush()
    db.session.refresh(new_activity)
    machine.current_activity_id = new_activity.id
    current_app.logger.debug(f"Starting {new_activity} on {machine}")
    db.session.commit()


def start_job(dt, machine: Machine, user_id: int, job_number, ideal_cycle_time_s):
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
    db.session.commit()
    starting_activity_code = machine.job_start_activity_id
    change_activity(dt,
                    machine,
                    new_activity_code_id=starting_activity_code,
                    user_id=user_id,
                    job_id=machine.active_job_id)


def end_job(dt, job):
    job.end_time = dt
    job.active = False
    db.session.commit()


def produced(time_end, quantity_good, quantity_rejects, job_id, machine_id, time_start=None):
    """ Record a production quantity. time_start and time_end mark the period of time in which the parts were created
    If time_start is not given, it is inferred from either the last ProductionQuantity or the start of the job"""
    if not time_start:
        job_production_quantities = ProductionQuantity.query.filter(ProductionQuantity.job_id == job_id).all()
        if len(job_production_quantities) > 0:
            last_pq = max(job_production_quantities, key=attrgetter('time_end'))
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
