from datetime import datetime

from flask import current_app

from app.default import events
from app.default.db_helpers import complete_last_activity
from app.default.models import Activity
from app.extensions import db
from app.login.models import UserSession
from config import Config


def end_all_user_sessions(user_id=None):
    """ End all sessions for a user or a machine (Either can be given)"""
    sessions = []
    if user_id:
        sessions.extend(UserSession.query.filter_by(user_id=user_id, active=True).all())
    else:
        sessions.extend(UserSession.query.filter_by(active=True).all())
    for us in sessions:
        current_app.logger.info(f"Ending user session {us}")
        us.end_session()
        # End all jobs assigned to the session
        for job in us.jobs:
            job.end_job()
        db.session.commit()  # Not committing here would sometimes cause sqlite to have too many operations
        # Set the activity to "no user"
        events.change_activity(datetime.now(),
                               us.machine,
                               new_activity_code_id=Config.NO_USER_CODE_ID,
                               user_id=user_id,
                               job_id=us.machine.active_job_id)
