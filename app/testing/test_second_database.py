import unittest

from app.android.helpers import get_valid_job_numbers


class SecondDatabaseTests(unittest.TestCase):

    def test_get_job_numbers(self):
        job_numbers = get_valid_job_numbers()
        self.assertIsNotNone(job_numbers)


if __name__ == "__main__":
    unittest.main()
