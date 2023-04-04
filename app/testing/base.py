import os
import unittest
from app.extensions import db

from app import create_app
from setup_database import setup_database


class BaseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ['TESTING'] = "True"
        from config import Config
        if "test" not in Config.db_name:
            raise Exception("'Test' not in db_name. Are you running tests on a production database? Set TESTING=True")
        cls.app = create_app()

    def setUp(self):
        self.app = create_app()
        with self.app.app_context():
            self.test_client = self.app.test_client()

    @classmethod
    def tearDownClass(cls) -> None:
        with cls.app.app_context():
            db.drop_all()
