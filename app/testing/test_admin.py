import unittest

from app.testing.base import BaseTest


class AdminTest(BaseTest):

    def test_routes(self):
        with self.test_client:
            self.app.config['LOGIN_DISABLED'] = True
            for route in ["/admin-home",
                          "/new-user",
                          "/change-password?user_id=1&action=reset_password",
                          "/edit-shift",
                          "/edit-machine?new=True",
                          "/edit-machine-group?machine_group_id=1",
                          "/edit-activity-code?ac_id=1"]:
                response = self.test_client.get(route)
                self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
