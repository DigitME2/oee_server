#!/usr/bin/env bash

export FLASK_APP=oee_webapp.py

# URI address of the database. If this is given, all other database variables are ignored
export DATABASE_URI=sqlite:///test.db


source venv/bin/activate
#flask run
exec gunicorn -b :8000 -m 007 "app:create_app()"
deactivate
