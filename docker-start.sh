#!/usr/bin/env bash

export FLASK_APP=oee_webapp.py

source venv/bin/activate
#flask run
exec gunicorn -b :8000 -m 007 "app:create_app()"
deactivate
