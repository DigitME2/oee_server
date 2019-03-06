import requests
import json
from random import randrange
from time import time, sleep


machine_number = 1
headers = {'Content-type': 'application/json'}

while 1:
    activities = []

    start = time()
    sleep(randrange(1, 10))
    end = time()
    rand = randrange(1, 10)
    if rand > 4:
        activity_code = 1
    else:
        activity_code = rand
    activity = {
      "activity_code": activity_code,
      "timestamp_start": start,
      "timestamp_end": end
    }
    activities.append(activity)
    data = {
        'machine_number': machine_number,
        'activities': activities
    }

    print("Sending activity: ", activity)
    print("Data: ", json.dumps(data))

    r = requests.post('http://localhost:5000/machineactivity', headers=headers, json=json.dumps(data))
