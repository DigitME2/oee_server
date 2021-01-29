FROM python:3.8

WORKDIR /home/oee_webapp

RUN apt-get update && apt-get install -y supervisor

COPY requirements-docker.txt requirements.txt
RUN pip install -r requirements.txt && pip install gunicorn

COPY app app
COPY migrations migrations
COPY celery_worker.py celery_worker.py
COPY docker-supervisord.conf supervisord.conf
COPY copy_to_docker_volume.sh copy_to_docker_volume.sh

# Copy some folders to a template folder. These will be copied to the /appdata volume on start
# This allows the appdata folder to be set as a volume, allowing it to be edited from the outside
COPY config.py /home/appdata_template/config.py
RUN mv /home/oee_webapp/app/static /home/appdata_template/static

# Create symlinks in the expected locations to point to the volume mapping
RUN ln -s /appdata/config.py config.py
RUN ln -s /appdata/static /home/oee_webapp/app/static

ENV FLASK_APP "app:create_app()"
ENV C_FORCE_ROOT=1

EXPOSE 8000
CMD ["/usr/bin/supervisord"]
