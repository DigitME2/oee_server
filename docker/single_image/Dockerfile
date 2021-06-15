# This should be run from the app root directory (one level below the docker and app folders)

FROM python:3.8

WORKDIR /home/oee_webapp

COPY /docker/single_image/requirements.txt requirements.txt
RUN pip install -r requirements.txt && pip install gunicorn

RUN apt-get update && apt-get install -y supervisor nginx redis

COPY app app
COPY migrations migrations
COPY celery_worker.py celery_worker.py
COPY /docker/single_image/supervisord.conf supervisord.conf
COPY /docker/single_image/example-config.py config.py

# Set up nginx
RUN rm /etc/nginx/sites-enabled/default
COPY /docker/single_image/nginx-server-conf /etc/nginx/sites-enabled/flask_oee

# Move the redis conf to the volume and create a symbolic link
RUN mkdir -p /data/redis
RUN mv /etc/redis/redis.conf /data/redis/redis.conf
RUN ln -s /data/redis/redis.conf /etc/redis/redis.conf

# Move the flask app's static folder to the /data directory so it will lie in the docker volume
RUN mv /home/oee_webapp/app/static /data/static
RUN ln -s /data/static /home/oee_webapp/app/static

ENV FLASK_APP "app:create_app()"
ENV C_FORCE_ROOT=1

EXPOSE 8000
CMD ["/usr/bin/supervisord"]
