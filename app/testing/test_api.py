import unittest
from datetime import datetime

import simple_websocket

from app.testing.base import BaseTest


class APITest(BaseTest):

    def test_create_activity(self):
        data = {
            "machine_id": 1,
            "activity_code_id": 2,
            "time_start": datetime.now().timestamp()
        }
        response = self.test_client.post('/api/machine-state-change', json=data)
        print(response)
        assert response.status_code == 200


    def test_get_oee(self):
        response = self.test_client.get('/api/oee?machine_id=1')
        print(response)
        assert response.status_code == 200


    def test_get_activity_durations(self):
        response = self.test_client.get('/api/activity-durations?machine_id=1')
        print(response)
        assert response.status_code == 200


if __name__ == '__main__':
    unittest.main()
