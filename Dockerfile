FROM python:3.8

RUN adduser --disabled-password --gecos "" oee

RUN apt-get update && apt-get -y install cron

# Cron job to control scheduled server tasks
COPY scheduled-server-cron /etc/cron.d/scheduled-server-tasks
RUN chmod 0644 /etc/cron.d/scheduled-server-tasks
RUN crontab /etc/cron.d/scheduled-server-tasks
RUN touch /var/log/cron.log
CMD cron && tail -f /var/log/cron.log

WORKDIR /home/oee_webapp

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn

COPY app app
COPY migrations migrations
COPY webapp.py start.sh ./
COPY config.py /config/config.py
RUN ln -s /config/config.py config.py
RUN chmod +x start.sh

ENV FLASK_APP webapp.py

RUN chown -R oee:oee ./
USER oee




EXPOSE 8000
ENTRYPOINT ["./start.sh"]
