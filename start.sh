#!/usr/bin/env bash

# This needs to be set for the CLI to work when run as a cron job
export FLASK_APP="app:create_app()"

#source venv/bin/activate
exec gunicorn -b :8000 -m 007 "app:create_app()"
deactivate
