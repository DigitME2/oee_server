import json
from datetime import datetime

from flask import request, current_app, abort

from app.android.helpers import parse_cycle_time
from app.android.workflow import PausableWorkflow, DefaultWorkflow, RunningTotalWorkflow
from app.default.db_helpers import get_current_machine_activity_id, complete_last_activity, get_assigned_machine
from app.default.models import Job, Activity, ActivityCode
from app.extensions import db
from app.login import bp
from app.login.helpers import start_user_session, end_user_sessions
from app.login.models import User, UserSession
from config import Config


@bp.route('/android-update-quantity', methods=['POST'])
def running_total_update_quantity():
    print(request.json)
    return {"success": True}