import unittest

from app.android.helpers import get_job_validation_dict
from config import Config


class SecondDatabaseTests(unittest.TestCase):

    def setUp(self) -> None:
        if not Config.USE_JOB_VALIDATION:
            self.skipTest("Job validation not enabled. Skipping test")

    def test_get_job_numbers(self):
        job_numbers = get_job_validation_dict()
        self.assertIsNotNone(job_numbers)


if __name__ == "__main__":
    unittest.main()
