#!/usr/bin/env bash

# Sends a POST request containing json from the file activity.json

curl -i -X PUT -H 'Content-Type: application/json' -d @activity1.json http://localhost:5000/machineactivity