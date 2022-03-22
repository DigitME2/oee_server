import unittest
from unittest.mock import MagicMock, patch

from flask_login import current_user

from app import login_manager, create_app
from app.login.models import User
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

    # Dont bother doing this, its too hard and ineffective with wtforms. Use selenium or something
    # def test_create_machine(self):
    #     with self.test_client:
    #         self.app.config['LOGIN_DISABLED'] = True
    #         data = {
    #             "name": "Machine 1",
    #             "active": True,
    #             "device_ip": "1.1.1.1",
    #             "workflow_type": "default",
    #             "group": 1,
    #             "job_start_input_type": "cycle_time_seconds",
    #             "schedule_id": 1
    #         }
    #         self.test_client.post('/editmachine?new=True', data=data)
    #         response =
    #         self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
