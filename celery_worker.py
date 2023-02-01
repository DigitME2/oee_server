#!/usr/bin/env python
import logging.config

# noinspection PyUnresolvedReferences
from app import celery_app, create_app  # This module needs access to celery_app


app = create_app()
app.app_context().push()
celery_app.conf.update(app.config)
celery_app.log.setup_task_loggers()
