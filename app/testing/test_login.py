from app.extensions import db
from app.login.models import User
from app.testing.base import BaseTest


class TestLogin(BaseTest):
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
