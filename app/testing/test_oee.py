import unittest
from datetime import datetime, time, timedelta

from app import create_app
from app.data_analysis.oee.availability import calculate_machine_availability
from app.default.db_helpers import create_all_scheduled_activities, create_day_scheduled_activities
from app.default.models import ScheduledActivity, Machine, Activity
from app.extensions import db
from app.setup_database import setup_database
from app.data_analysis.oee import availability, quality, performance
from config import Config


class OEETests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        with self.app.app_context():
            db.create_all()
            setup_database()

    def tearDown(self) -> None:
        pass

    def test_availibility(self):
        with self.app.app_context():
            print("Testing availibility")
            # Create scheduled activities for a demo machine
            machine = Machine.query.get(1)
            day_start = datetime.combine(date=datetime.now().date(), time=time(hour=0, minute=0, second=0, microsecond=0))
            day_end = day_start + timedelta(days=1)
            create_day_scheduled_activities(machine, shift_start=day_start + timedelta(hours=9), shift_end=day_start + timedelta(hours=18), create_date=datetime.now().date())
            act = Activity(machine_id=machine.id,
                           activity_code_id=Config.UPTIME_CODE_ID,
                           machine_state=Config.MACHINE_STATE_RUNNING,
                           time_start=day_start + timedelta(hours=9),
                           time_end=day_start + timedelta(hours=18))
            db.session.add(act)
            db.session.commit()

            availibility = calculate_machine_availability(machine.id, time_start=day_start, time_end=day_end)

            self.assertEqual(availibility, 1)



if __name__ == "__main__":
    unittest.main()
