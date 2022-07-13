import os
from datetime import datetime

import requests

data = {
    "machine_id": os.environ.get("machine_id") or 1,
    "machine_state": os.environ.get("machine_state") or 0,
    "time_start": datetime.now().timestamp()
}
response = requests.post('http://localhost:5000/api/machine-state-change', json=data)
print(response)
