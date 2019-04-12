import requests
import json
from random import randrange
from time import time, sleep
from app.default.models import MACHINE_STATE_RUNNING


machine_id = 1
headers = {'Content-type': 'application/json'}

while 1:
    for i in range(0, 3):
        machine_state = i
        start = time()
        if i == MACHINE_STATE_RUNNING:
            sleep(randrange(6, 10))
        else:
            sleep(randrange(0, 4))
        end = time()

        activity = {
            "machine_id": machine_id,
            "machine_state": machine_state,
            "timestamp_start": start,
            "timestamp_end": end
        }
        print("POST: ", json.dumps(activity))

        r = requests.post('http://localhost:5000/activity', headers=headers, json=json.dumps(activity))
        print("Response: ", r.status_code, r.content)
