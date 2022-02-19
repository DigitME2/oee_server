import re
import unittest

from flask import current_app

from app.default.models import Machine
from app.login.helpers import start_user_session, end_user_sessions
from app.login.models import User
from app import create_app
from app.extensions import db
from app.setup_database import setup_database


class TestLogin(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        with self.app.app_context():
            setup_database()
            self.test_client = self.app.test_client()

    def test_routes(self):
        response = self.test_client.get('/login')
        self.assertEqual(response.status_code, 200)

    def test_login(self):
        with self.app.app_context():
            username = "test"
            password = "test"
            u = User(username=username)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            success_response = self.test_client.post('/login', data={username: username, password: password})
            fail_response = self.test_client.post('/login', data={username: username, password: "1234qwerasdf"})
            self.assertEqual(success_response.status_code, 200)

    def test_user_sessions(self):
        with self.app.app_context():
            m = Machine(name="test", device_ip="0.0.0.0")
            db.session.add(m)
            db.session.commit()
            self.assertTrue(start_user_session(user_id=1, device_ip="0.0.0.0"))
            end_user_sessions(user_id=1)






if __name__ == '__main__':
    unittest.main()