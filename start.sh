#!/usr/bin/env bash

export FLASK_APP=oee_webapp.py

# URI address of the database. If this is given, all other database variables are ignored
export DATABASE_URI=sqlite:///test.db

#export DATABASE_USER=postgres
#export DATABASE_ADDRESS=localhost
#export DATABASE_PORT=5432
#export DATABASE_NAME=prod
#export DATABASE_PASSWORD=

source venv/bin/activate
#flask run
gunicorn --workers 5 --bind localhost:8001 -m 007 "app:create_app()"
deactivate
