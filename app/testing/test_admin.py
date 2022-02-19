import unittest
from unittest.mock import Mock, MagicMock, patch

from app import create_app
from app.login.models import User


class AdminTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.config['LOGIN_DISABLED'] = True
        with self.app.app_context():
            self.test_client = self.app.test_client()
            self.app.current_user = MagicMock(return_value=User.query.get(1))
            self.app.current_user.admin = MagicMock(return_value=True)

    @patch('flask_login.utils._get_user')
    def test_routes(self):
        for route in ["/adminhome", "/settings", "/newuser", "/changepassword", "/schedule", "/editmachine",
                      "/editmachinegroup", "/editactivitycode"]:
            response = self.test_client.get(route)
            self.assertEqual(response.status_code, 200)  # add assertion here


if __name__ == '__main__':
    unittest.main()
