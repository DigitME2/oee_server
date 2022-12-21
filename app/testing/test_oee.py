import unittest
from datetime import datetime, time, timedelta

from app.data_analysis.oee.availability import get_machine_availability
from app.default.helpers import create_all_scheduled_activities
from app.default.models import Machine, Activity
from app.extensions import db
from app.testing.base import BaseTest
from config import Config


class OEETests(BaseTest):

    def test_availability(self):
        with self.app.app_context():
            print("Testing availability")
            # Create scheduled activities for a demo machine
            machine = Machine.query.get(1)
            day_start = datetime.combine(date=datetime.now().date(), time=time(hour=0, minute=0, second=0, microsecond=0))
            day_end = day_start + timedelta(days=1)
            create_all_scheduled_activities()
            act = Activity(machine_id=machine.id,
                           activity_code_id=Config.UPTIME_CODE_ID,
                           machine_state=Config.MACHINE_STATE_UPTIME,
                           time_start=day_start + timedelta(hours=9),
                           time_end=day_start + timedelta(hours=18))
            db.session.add(act)
            db.session.commit()

            availability = get_machine_availability(machine.id, time_start=day_start, time_end=day_end)

            self.assertEqual(availability, 1)



if __name__ == "__main__":
    unittest.main()
