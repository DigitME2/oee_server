from datetime import datetime

from flask import current_app

from app import db
from app.default.models import InputDevice, Activity, Machine, Job
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


def change_activity(dt: datetime, machine: Machine, new_activity_code_id: int, user_id: int, job_id: int):
    if new_activity_code_id == Config.UPTIME_CODE_ID:
        machine_state = 1
    else:
        machine_state = 0
    # End the current activity
    if machine.current_activity:
        current_activity = machine.current_activity
        current_activity.time_end = dt

    # Start a new activity with no user
    new_activity = Activity(machine_id=machine.id,
                            time_start=dt,
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


def end_job(dt, job, quantity_produced, quantity_rejects):
    job.end_time = dt
    job.active = False
    job.quantity_produced += quantity_produced
    job.quantity_rejects += quantity_rejects
    db.session.commit()
