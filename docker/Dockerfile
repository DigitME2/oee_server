# This should be run from the app root directory (one level below the docker and app folders)

FROM python:3.8

RUN apt-get update && apt-get install -y supervisor nginx npm

# Set up JS libraries
RUN mkdir -p /home/oee_webapp/app/static
WORKDIR /home/oee_webapp/app/static
COPY /app/static/package.json .
RUN npm install

WORKDIR /home/oee_webapp

COPY /docker/requirements.txt requirements.txt
RUN pip install -r requirements.txt && pip install gunicorn

COPY app app
COPY migrations migrations
COPY celery_worker.py celery_worker.py
COPY /docker/Dockerfile Dockerfile
COPY /docker/supervisord.conf supervisord.conf
COPY /docker/example-config.py config.py

ENV FLASK_APP "app:create_app()"
ENV C_FORCE_ROOT=1

EXPOSE 8000
CMD ["/usr/bin/supervisord"]
