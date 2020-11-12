#!/usr/bin/env bash

exec gunicorn -b :8000 -m 007 "app:create_app()"

