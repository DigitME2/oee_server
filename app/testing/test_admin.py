import unittest

from app.testing.base import BaseTest


class AdminTest(BaseTest):

    def test_routes(self):
        with self.test_client:
            self.app.config['LOGIN_DISABLED'] = True
            for route in ["/adminhome",
                          "/settings",
                          "/newuser",
                          "/changepassword?user_id=1",
                          "/schedule",
                          "/editmachine?machine_id=1",
                          "/editmachinegroup?machine_group_id=1",
                          "/editactivitycode?ac_id=1"]:
                response = self.test_client.get(route)
                self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
