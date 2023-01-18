from datetime import datetime
from operator import attrgetter
from typing import Optional

from flask import current_app
from flask_login import current_user

from app.default.helpers import get_machine_activities
from app.extensions import db
from app.default.models import InputDevice, Activity, Machine, Job, ProductionQuantity, ActivityCode
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


def change_activity(dt: datetime, machine: Machine, new_activity_code_id: int, user_id: int, job_id: Optional[int]):
    # TODO Prevent uptime without job
    new_activity_code = ActivityCode.query.get_or_404(new_activity_code_id)
    machine_state = new_activity_code.machine_state
    # If the activity is uptime during planned downtime, record it as overtime
    if machine.schedule_state == Config.MACHINE_STATE_PLANNED_DOWNTIME and machine_state == Config.MACHINE_STATE_UPTIME:
        machine_state = Config.MACHINE_STATE_OVERTIME

    # End the current activity
    if machine.current_activity:
        current_activity = machine.current_activity
        current_activity.end_time = dt

    # Start a new activity with no user
    new_activity = Activity(machine_id=machine.id,
                            start_time=dt,
                            activity_code_id=new_activity_code_id,
                            user_id=user_id,
                            job_id=job_id)
    db.session.add(new_activity)
    db.session.flush()
    db.session.refresh(new_activity)
    machine.current_activity_id = new_activity.id
    current_app.logger.debug(f"Starting {new_activity} on {machine}")
    db.session.commit()


def start_job(dt, machine: Machine, user_id: int, job_number, ideal_cycle_time_s, retroactively=False) -> Job:
    # Create the job
    job = Job(start_time=dt,
              job_number=job_number,
              machine_id=machine.id,
              ideal_cycle_time_s=ideal_cycle_time_s,
              active=True)
    db.session.add(job)
    if not retroactively:
        # Don't create activities or set the active job if this job is being added retroactively
        db.session.flush()
        db.session.refresh(job)
        machine.active_job_id = job.id
        starting_activity_code = machine.job_start_activity_id
        change_activity(dt,
                        machine,
                        new_activity_code_id=starting_activity_code,
                        user_id=user_id,
                        job_id=machine.active_job_id)
    db.session.commit()
    return job


def end_job(dt, job: Job, retroactively=False):
    # Set the activity to down
    new_activity_code = Config.UNEXPLAINED_DOWNTIME_CODE_ID
    if job.machine.schedule_state == Config.MACHINE_STATE_PLANNED_DOWNTIME:
        new_activity_code = Config.PLANNED_DOWNTIME_CODE_ID
    if not retroactively:
        # Don't create activities or set the active job if this job is being added retroactively
        job.machine.active_job_id = None
        change_activity(dt=dt,
                        machine=job.machine,
                        new_activity_code_id=new_activity_code,
                        user_id=current_user.id,
                        job_id=job.id)
    job.end_time = dt
    job.active = False
    db.session.commit()


def produced(time_end, quantity_good, quantity_rejects, job_id, machine_id, time_start=None):
    """ Record a production quantity. time_start and time_end mark the period of time in which the parts were created
    If time_start is not given, it is inferred from either the last ProductionQuantity or the start of the job"""
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
    if machine.current_activity.activity_code_id == Config.PLANNED_DOWNTIME_CODE_ID:
        # Set to the standard unplanned downtime activity
        change_activity(dt, machine=machine, new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                        user_id=machine.active_user_id, job_id=machine.active_job_id)
    # Otherwise we keep the same activity code and call change_activity to handle the change in machine_state
    else:
        change_activity(dt, machine=machine, new_activity_code_id=machine.current_activity.activity_code_id,
                        user_id=machine.active_user_id, job_id=machine.active_job_id)


def end_shift(dt: datetime, machine):
    """ Run a shift change on a machine"""
    machine.schedule_state = Config.MACHINE_STATE_PLANNED_DOWNTIME
    db.session.commit()
    if not machine.active_job:
        # If the machine is in unplanned downtime (as expected)
        if machine.current_activity.activity_code.machine_state == Config.MACHINE_STATE_UNPLANNED_DOWNTIME:
            change_activity(dt, machine=machine, new_activity_code_id=Config.PLANNED_DOWNTIME_CODE_ID,
                            user_id=machine.active_user_id, job_id=machine.active_job_id)
        # If machine is in planned downtime, make no change
    # If there's a job active keep the same activity
    else:
        # Call change activity if the machine is up so that it changes to overtime
        if machine.current_activity.activity_code.machine_state == Config.MACHINE_STATE_UPTIME:
            change_activity(dt, machine=machine, new_activity_code_id=Config.UNEXPLAINED_DOWNTIME_CODE_ID,
                            user_id=machine.active_user_id, job_id=machine.active_job_id)
        # If machine is down during a job, make no change. The machine will be set to planned downtime on job end.


# FIXME This is being a bit dodgy and creating extra activities sometimes (or maybe editing existing ones incorrectly)
def modify_activity(dt: datetime, modified_act: Activity, new_start: datetime, new_end: datetime, new_activity_code_id):
    """ Modify an existing activity in the past, as well as other activities affected by the times being changed """
    # Account for activities that will be overlapped by the changed times
    overlapped_activities = get_machine_activities(machine=modified_act.machine, time_start=new_start, time_end=new_end)
    for act in overlapped_activities:
        if act.id == modified_act.id:
            continue
        # If the new activity completely overlaps this activity
        if act.start_time >= new_start and act.end_time and act.end_time <= new_end:
            db.session.delete(act)
            current_app.logger.debug(f"Deleting {act}")
        # If the new activity overlaps the end of this activity
        elif act.end_time and new_start < act.end_time < new_end:
            act.end_time = new_start
            current_app.logger.debug(f"Shortening end of {act}")
        # If the new activity overlaps the start of this activity
        elif new_start < act.start_time < new_end:
            act.start_time = new_end
            current_app.logger.debug(f"Shortening start of {act}")
        # If the new activity is completely inside another activity we'll need to make another, third activity
        elif act.start_time < new_end < act.end_time and act.start_time < new_start < act.end_time:
            final_end_time = act.end_time
            third_activity = Activity(machine_id=act.machine_id,
                                      explanation_required=act.explanation_required,
                                      start_time=new_end,
                                      end_time=final_end_time,
                                      activity_code_id=act.activity_code_id,
                                      job_id=act.job_id,
                                      user_id=act.user_id)

            current_app.logger.debug(f"Creating new activity {third_activity}")
            db.session.add(third_activity)
            act.end_time = new_start
    # Account for gaps that will be created by an activity shrinking
    if new_start > modified_act.start_time:
        # Adjust the end time for the activity in front of the modified activity
        prequel_activity = Activity.query.filter(Activity.end_time == modified_act.start_time).first()
        prequel_activity.end_time = new_start
        current_app.logger.debug(f"lengthening end of {prequel_activity}")
    if new_end < modified_act.end_time:
        # Adjust the start time for the activity after the modified activity
        sequel_activity = Activity.query.filter(Activity.start_time == modified_act.end_time).first()
        sequel_activity.start_time = new_end
        current_app.logger.debug(f"lengthening start of {sequel_activity}")
    modified_act.activity_code_id = new_activity_code_id
    modified_act.start_time = new_start
    modified_act.end_time = new_end
    db.session.commit()


def modify_job(now, modified_job: Job, new_start, new_end, ideal_cycle_time, job_number):
    # Create the job
    modified_job.start_time = new_start
    modified_job.end_time = new_end
    modified_job.job_number = job_number
    modified_job.ideal_cycle_time_s = ideal_cycle_time
    db.session.commit()
