FROM python:3.8

WORKDIR /home/oee_webapp

RUN apt-get update && apt-get install -y supervisor

COPY requirements-docker.txt requirements.txt
RUN pip install -r requirements.txt && pip install gunicorn

COPY ../../app app
COPY ../../migrations migrations
COPY ../../celery_worker.py celery_worker.py
COPY docker-supervisord.conf supervisord.conf

# Link some folders to the appdata folder, which will be mapped to a volume
COPY config-docker.py /home/appdata/config.py
RUN mv /home/oee_webapp/app/static /home/appdata/static

# Copy the nginx config file to the appdata folder so any nginx images can share the same volume
COPY nginx-default.conf /home/appdata/default.conf

# Create symlinks in the expected locations to point to the volume mapping
RUN ln -s /home/appdata/config.py config.py
RUN ln -s /home/appdata/static /home/oee_webapp/app/static

ENV FLASK_APP "app:create_app()"
ENV C_FORCE_ROOT=1

EXPOSE 8000
CMD ["/usr/bin/supervisord"]
