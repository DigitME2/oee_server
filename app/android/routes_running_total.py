import json

from flask import request, current_app

from app.default.models import Job
from app.extensions import db
from app.login import bp
from app.login.models import UserSession


@bp.route('/android-update-quantity', methods=['POST'])
def running_total_update_quantity():
    user_session = UserSession.query.filter_by(device_ip=request.remote_addr, active=True).first()

    try:
        quantity_produced = int(request.json["quantity_produced"])
        quantity_rejects = int(request.json["rejects"])
    except KeyError:
        current_app.logger.error(f"Received incorrect data from {user_session} while updating quantity")
        return json.dumps({"success": False,
                           "reason": "Server error parsing data"})

    # Update quantities for the current job
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    current_job.quantity_produced += quantity_produced
    current_job.quantity_rejects += quantity_rejects
    db.session.commit()

    return json.dumps({"quantity_produced": current_job.quantity_produced,
                       "quantity_rejects": current_job.quantity_rejects})
