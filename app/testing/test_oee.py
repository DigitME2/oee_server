import unittest
from datetime import datetime, time, timedelta

from app.data_analysis.oee.availability import get_machine_availability
from app.default.models import Machine, Activity
from app.extensions import db
from app.testing.base import BaseTest
from config import Config


class OEETests(BaseTest):

    def test_availability(self):
        ...
        # todo




if __name__ == "__main__":
    unittest.main()
