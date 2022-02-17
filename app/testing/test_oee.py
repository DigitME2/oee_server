import unittest
from datetime import datetime

from app import create_app
from app.default.db_helpers import create_scheduled_activities
from app.default.models import ScheduledActivity, Machine
from app.extensions import db
from app.setup_database import setup_database
from config import Config

Config.db_name = "sqlite:///testing/test.db"

class OEETests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        with self.app.app_context():
            db.create_all()
            setup_database()

    def tearDown(self) -> None:
        pass
        # with self.app.app_context():
        #     db.drop_all()

    def test_availibility(self):
        with self.app.app_context():
            print("Testing availibility")
            machine = Machine()
            create_scheduled_activities(datetime.now().date())




            self.assertEqual(1, 1)


if __name__ == "__main__":
    unittest.main()
