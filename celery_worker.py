#!/usr/bin/env python
from app import celery_app, create_app  # This module needs access to celery_app

app = create_app()
app.app_context().push()
