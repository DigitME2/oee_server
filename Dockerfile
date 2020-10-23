FROM debian:latest
#FROM ubuntu:20.04
#FROM python:3.8 switched from this to ubuntu trying to get cron working

RUN adduser --disabled-password --gecos "" oee

RUN apt-get update && apt-get -y install cron

# Cron job to control scheduled server tasks
COPY scheduled-server-cron /etc/cron.d/scheduled-server-tasks
RUN chmod 0644 /etc/cron.d/scheduled-server-tasks
RUN crontab /etc/cron.d/scheduled-server-tasks
RUN touch /var/log/cron.log
CMD cron && tail -f /var/log/cron.log

WORKDIR /home/oee_webapp

# had to do this for ubuntu
RUN apt-get install -y python3
RUN apt-get install -y python3-pip

COPY requirements-docker.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN pip3 install gunicorn

COPY app app
COPY migrations migrations
COPY webapp.py start.sh ./
COPY config.py /config/config.py
RUN ln -s /config/config.py config.py
RUN chmod +x start.sh

ENV FLASK_APP "app:create_app()"

RUN chown -R oee:oee ./
USER oee




EXPOSE 8000
ENTRYPOINT ["./start.sh"]
