import requests
import json
from random import randrange
from time import time, sleep


machine_number = 1
headers = {'Content-type': 'application/json'}

while 1:
    for i in range(0, 3):
        machine_state = i
        start = time()
        sleep(randrange(0, 6))
        end = time()

        activity = {
            "machine_number": machine_number,
            "machine_state": machine_state,
            "timestamp_start": start,
            "timestamp_end": end
        }
        print("POST: ", json.dumps(activity))

        r = requests.post('http://localhost:5000/activity', headers=headers, json=json.dumps(activity))
        print("Response: ", r.status_code, r.content)
