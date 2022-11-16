import unittest

from app.android.helpers import get_job_validation_dict


class SecondDatabaseTests(unittest.TestCase):

    def test_get_job_numbers(self):
        job_numbers = get_job_validation_dict()
        self.assertIsNotNone(job_numbers)


if __name__ == "__main__":
    unittest.main()
