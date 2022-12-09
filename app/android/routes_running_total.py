import json
from datetime import datetime

import redis
from flask import request, current_app

from app.default import events
from app.default.models import Job, InputDevice, ProductionQuantity
from app.extensions import db
from app.login import bp
from config import Config

r = redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)


@bp.route('/android-update-quantity', methods=['POST'])
def running_total_update_quantity():
    now = datetime.now()
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
    current_job = input_device.machine.active_job
    current_job.quantity_produced += quantity_produced
    current_job.quantity_rejects += quantity_rejects
    db.session.commit()

    events.produced(now, quantity_produced, quantity_rejects, current_job.id, input_device.machine.id)

    r.set(f"job_{current_job.id}_last_update", now.timestamp(), ex=86400)

    return json.dumps({"success": True,
                       "quantity_produced": current_job.quantity_produced,
                       "quantity_rejects": current_job.quantity_rejects,
                       "last_update": now.timestamp()})
