#!/usr/bin/env bash
# Install requirements
apt update && apt install -y npm redis virtualenv nginx

# Copy default config
cp ./example-confs/config.py.example config.py

# install npm package in /app/static
npm --prefix ./app/static install ./app/static

# Set up virtual environment
virtualenv venv
./venv/bin/pip install -r requirements.txt

# install gunicorn
./venv/bin/pip install gunicorn

# Copy systemd files
sudo cp ./example-confs/oee_celery_beat.service /etc/systemd/system
sudo cp ./example-confs/oee_server.service /etc/systemd/system
sudo cp ./example-confs/oee_discovery.service /etc/systemd/system
sudo cp ./example-confs/oee_celery.service /etc/systemd/system

# Edit default values (user, working directory) in example systemd files
sudo sed -i 's&(USERNAME)&'$USER'&g' /etc/systemd/system/oee_server.service /etc/systemd/system/oee_celery.service /etc/systemd/system/oee_celery_beat.service /etc/systemd/system/oee_discovery.service
sudo sed -i 's&/home/user/oee_server&'$PWD'&g' /etc/systemd/system/oee_server.service /etc/systemd/system/oee_celery.service /etc/systemd/system/oee_celery_beat.service /etc/systemd/system/oee_discovery.service

# Enable & start services
sudo systemctl daemon-reload
sudo systemctl enable oee_server oee_discovery oee_celery oee_celery_beat
sudo systemctl start oee_server oee_discovery oee_celery oee_celery_beat

# Set up Nginx
sudo unlink /etc/nginx/sites-enabled/default
sudo cp ./example-confs/nginx-conf-example /etc/nginx/sites-available
sudo ln -s /etc/nginx/sites-available/nginx-conf-example /etc/nginx/sites-enabled
sudo nginx -s reload
sudo ufw allow 'Nginx Full'

