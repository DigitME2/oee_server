from datetime import datetime

from flask import current_app

from app import db
from app.default import events
from app.default.helpers import get_machine_activities
from app.default.models import Activity, Job


# FIXME This is being a bit dodgy and creating extra activities sometimes (or maybe editing existing ones incorrectly)
def modify_activity(modified_act: Activity, new_start: datetime, new_end: datetime, new_activity_code_id):
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


def modify_job(job: Job, new_start, new_end, ideal_cycle_time, job_number, quantity_good,
               quantity_rejects):
    time_modified = (job.start_time != new_start or
                     job.end_time != new_end)
    job.start_time = new_start
    job.end_time = new_end
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
        qty_modified = (quantity_good != job.get_total_good_quantity() or
                        quantity_rejects != job.get_total_reject_quantity())
        if qty_modified:
            raise NotImplementedError
        else:
            raise NotImplementedError
            # TODO Implement. First step check if the time change will completely remove a ProductionQuantity entry
            #  or just shorten/lengthen the entries. If the former, tell the user to change PQs manually first. If
            #  the latter, just adjust the times
