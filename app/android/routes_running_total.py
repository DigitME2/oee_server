import json
from datetime import datetime

import redis
from flask import request, current_app

from app.default.models import Job, InputDevice, ProductionQuantity
from app.extensions import db
from app.login import bp
from config import Config

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)


@bp.route('/android-update-quantity', methods=['POST'])
def running_total_update_quantity():
    device_uuid = request.json["device_uuid"]
    input_device = InputDevice.query.filter_by(uuid=device_uuid).first()
    user_session = input_device.active_user_session

    try:
        quantity_produced = int(request.json["quantity_produced"])
        quantity_rejects = int(request.json["rejects"])
    except KeyError:
        current_app.logger.error(f"Received incorrect data from {user_session} while updating quantity")
        return json.dumps({"success": False,
                           "reason": "Server error parsing data"})

    # Update quantities for the current job
    current_job = Job.query.filter_by(user_session_id=user_session.id, active=True).first()
    production_quantity = ProductionQuantity(quantity_produced=quantity_produced,
                                             time=datetime.now(),
                                             quantity_rejects=quantity_rejects,
                                             job_id=current_job.id)
    db.session.add(production_quantity)
    current_job.quantity_produced += quantity_produced
    current_job.quantity_rejects += quantity_rejects
    db.session.commit()

    timestamp = datetime.now().timestamp()
    r.set(f"job_{current_job.id}_last_update", timestamp, ex=86400)

    return json.dumps({"success": True,
                       "quantity_produced": current_job.quantity_produced,
                       "quantity_rejects": current_job.quantity_rejects,
                       "last_update": timestamp})
