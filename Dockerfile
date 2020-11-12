FROM python:3.8

WORKDIR /home/oee_webapp

COPY requirements-docker.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install gunicorn

COPY app app
COPY migrations migrations
COPY docker-start.sh ./
COPY config.py /config/config.py
RUN ln -s /config/config.py config.py
RUN chmod +x docker-start.sh

ENV FLASK_APP "app:create_app()"

EXPOSE 8000
ENTRYPOINT ["./docker-start.sh"]
