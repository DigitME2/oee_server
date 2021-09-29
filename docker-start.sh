#!/usr/bin/env bash
# Something was causing the worker to hang and timeout. setting timeout to 1000 fixed this. Don't know why.

exec gunicorn -b :8000 -m 007 --timeout 1000 "app:create_app()"

