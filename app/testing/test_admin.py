import unittest
from unittest.mock import MagicMock, patch

from flask_login import current_user

from app import login_manager
from app.login.models import User
from app.testing.base import BaseTest


class AdminTest(BaseTest):
    def setUp(self) -> None:
        super().setUp()
        # with self.app.app_context():
        #     self.app.current_user = MagicMock(return_value=User.query.get(1))
        #     self.app.current_user.admin = MagicMock(return_value=True)

    # @patch('flask_login.utils._get_user')
    @login_manager.request_loader
    def test_routes(self):
        with self.test_client:
            response = self.test_client.post('/login', data={"username": "admin", "password": "digitme2"})
            t = current_user.username
            for route in ["/adminhome", "/settings", "/newuser", "/changepassword", "/schedule", "/editmachine",
                          "/editmachinegroup", "/editactivitycode"]:
                response = self.test_client.get(route)
                self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
