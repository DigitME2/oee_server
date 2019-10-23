from app.default import db_helpers
from app.default.models import Machine
from app.login.models import User

machine = Machine.query.get(1)
user = User.query.get(1)

db_helpers.create_daily_scheduled_activities(False)

pass