from datetime import datetime

from flask import current_app

from app import db
from app.default import events
from app.default.events import UptimeWithoutJobError
from app.default.helpers import get_machine_activities, get_jobs
from app.default.models import Activity, Job, Machine, ProductionQuantity
from config import Config


def add_past_activity(start_time, end_time, activity_code_id, machine_id):
    activity = Activity(start_time=start_time, end_time=end_time, activity_code_id=activity_code_id,
                        machine_id=machine_id)
    db.session.add(activity)
    db.session.commit()

    # Call modify activity with the same values, to rearrange other activities
    modify_activity(modified_act=activity, new_start=activity.start_time, new_end=activity.end_time,
                    new_activity_code=activity.activity_code)
    return activity


def modify_activity(modified_act: Activity, new_start: datetime, new_end: datetime, new_activity_code):
    """ Modify an existing activity in the past, as well as other activities affected by the times being changed """
    # Don't modify the times if everything matches but the seconds. (e.g. to stop 12:12:34 getting set to 12:12:00)
    # The user doesn't enter seconds in the web form
    everything_but_seconds = "%Y%m%d%H%M"
    if new_end.strftime(everything_but_seconds) == modified_act.end_time.strftime(everything_but_seconds):
        new_end = modified_act.end_time
    if new_start.strftime(everything_but_seconds) == modified_act.start_time.strftime(everything_but_seconds):
        new_start = modified_act.start_time
    # Check for uptime being created without a job
    jobs = get_jobs(new_start, new_end, modified_act.machine)
    activity_is_up = (new_activity_code.machine_state in [Config.MACHINE_STATE_UPTIME, Config.MACHINE_STATE_OVERTIME])
    if activity_is_up:
        if len(jobs) != 1:
            raise UptimeWithoutJobError
        else:
            latest_start_time = jobs[0].end_time or datetime.now()
            activity_runs_outside_job = (new_start < jobs[0].start_time or new_end > latest_start_time)
            if activity_is_up and (len(jobs) != 1 or activity_runs_outside_job):
                raise UptimeWithoutJobError
    # TODO Check that the indirect modifications don't cause uptime without a job
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
    modified_act.activity_code_id = new_activity_code.id
    modified_act.start_time = new_start
    modified_act.end_time = new_end
    db.session.commit()


def split_activity(activity, split_time: datetime):
    """ Splits an activity into two with the same values, ending/starting at the split_time"""
    start = activity.start_time
    end = activity.end_time
    activity_code_id = activity.activity_code_id
    machine_id = activity.machine_id
    db.session.delete(activity)
    # First activity
    add_past_activity(start_time=start, end_time=split_time, activity_code_id=activity_code_id, machine_id=machine_id)
    # Second activity
    add_past_activity(start_time=split_time, end_time=end, activity_code_id=activity_code_id, machine_id=machine_id)
    db.session.commit()


def add_past_job(start, end, machine, ideal_cycle_time, job_number, quantity_good, quantity_rejects):
    existing_jobs = get_jobs(start, end, machine)
    if len(existing_jobs) > 0:
        raise OverlappingJobsError
    job = Job(start_time=start,
              end_time=end,
              job_number=job_number,
              machine_id=machine.id,
              ideal_cycle_time_s=ideal_cycle_time,
              active=False)
    db.session.add(job)
    db.session.commit()
    events.produced(time_end=end,
                    quantity_good=quantity_good,
                    quantity_rejects=quantity_rejects,
                    job_id=job.id,
                    machine_id=machine.id)


def modify_job(job: Job, new_start, new_end, ideal_cycle_time, job_number, quantity_good,
               quantity_rejects):
    # Don't modify the times if everything matches but the seconds. (e.g. to stop 12:12:34 getting set to 12:12:00)
    everything_but_seconds = "%Y%m%d%H%M"
    if new_end and new_end.strftime(everything_but_seconds) == job.end_time.strftime(everything_but_seconds):
        new_end = job.end_time
    if new_start and new_start.strftime(everything_but_seconds) == job.start_time.strftime(everything_but_seconds):
        new_start = job.start_time

    if new_end is None:
        existing_jobs = get_jobs(new_start, datetime.now(), job.machine)
    else:
        existing_jobs = get_jobs(new_start, new_end, job.machine)
    if len(existing_jobs) > 1:
        raise OverlappingJobsError
    if len(existing_jobs) == 1 and existing_jobs[0].id != job.id:
        raise OverlappingJobsError
    time_modified = (job.start_time != new_start or
                     job.end_time != new_end)
    qty_modified = (quantity_good != job.get_total_good_quantity() or
                    quantity_rejects != job.get_total_reject_quantity())
    job.start_time = new_start
    job.job_number = job_number
    job.ideal_cycle_time_s = ideal_cycle_time
    db.session.commit()

    # Modify production_quantities
    if new_end:
        pq_end = new_end
    elif job.active:
        pq_end = datetime.now()
    else:
        pq_end = job.end_time
    if len(job.quantities) == 1:
        job.quantities[0].start_time = new_start
        job.quantities[0].end_time = pq_end
        job.quantities[0].quantity_good = quantity_good
        job.quantities[0].quantity_rejects = quantity_rejects
        db.session.commit()
    elif len(job.quantities) == 0 and quantity_rejects + quantity_good > 0:
        events.produced(time_end=pq_end, quantity_good=quantity_good, quantity_rejects=quantity_rejects,
                        job_id=job.id, machine_id=job.machine_id, time_start=new_start)
    else:
        if qty_modified:
            raise IntegrityError
        elif time_modified:
            raise NotImplementedError
            # TODO Implement. First step check if the time change will completely remove a ProductionQuantity entry
            #  or just shorten/lengthen the entries. If the former, tell the user to change PQs manually first. If
            #  the latter, just adjust the times
        else:
            return


def modify_production_record(record: ProductionQuantity, time_start, time_end, quantity_good, quantity_rejects):
    """ Record a production quantity. time_start and time_end mark the period of time in which the parts were created
    If time_start is not given, it is inferred from either the last ProductionQuantity or the start of the job"""
    # TODO Check there is uptime in the duration, or raise an exception
    # TODO Check it remains in the time of the job
    record.start_time = time_start
    record.end_time = time_end
    record.quantity_good = quantity_good
    record.quantity_rejects = quantity_rejects
    db.session.commit()


def add_past_production_record(time_start, time_end, quantity_good, quantity_rejects, job_id, machine_id):
    """ Record a production quantity in the past. time_start and time_end mark the period of time in which the parts
     were created. """
    # TODO Check there is uptime in the duration, or raise an exception
    # TODO Check the record is in the job
    production_quantity = ProductionQuantity(start_time=time_start,
                                             end_time=time_end,
                                             quantity_good=quantity_good,
                                             quantity_rejects=quantity_rejects,
                                             job_id=job_id,
                                             machine_id=machine_id)
    db.session.add(production_quantity)
    db.session.commit()

class IntegrityError(Exception):
    pass


class OverlappingJobsError(Exception):
    pass