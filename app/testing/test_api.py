import unittest
import simple_websocket
import requests
from datetime import datetime, timedelta

from flask_table import Table

from app.testing.base import BaseTest
from app.visualisation.tables import get_oee_table


class APITest(BaseTest):

    def test_create_activity(self):
        data = {
            "machine_id": 1,
            "activity_code_id": 2,
            "time_start": datetime.now().timestamp()
        }
        response = self.test_client.post('/api/activity', json=data)
        print(response)
        assert response.status_code == 200

    def test_websocket(self):
        ws = simple_websocket.Client('ws://localhost:5000/activity-updates')
        try:
            while True:
                ws.send(1)
                data = ws.receive()
        except (KeyboardInterrupt, EOFError, simple_websocket.ConnectionClosed):
            ws.close()


if __name__ == '__main__':
    unittest.main()