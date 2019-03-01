#!/usr/bin/env bash

# Sends a PUT request containing json from the file activity.json

curl -i -X Put -H 'Content-Type: application/json' -d @activity1.json http://localhost:5000/machineactivity