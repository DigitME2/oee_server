#!/usr/bin/env bash

if [ "$EUID" -ne 0 ]
  then echo "Please run with sudo"
  exit
fi

# Install requirements
echo "Installing apt packages..."
apt-get update -qqq
apt-get install -qq -y git npm redis virtualenv nginx > /dev/null

echo "Downloading from github..."
git clone https://github.com/DigitME2/oee_server.git ~/oee_server --quiet --branch production --depth=1
cd ~/oee_server

# Copy default config
cp ./example-confs/config.py.example config.py

# install npm package in /app/static
echo "Running npm install..."
npm --prefix ./app/static install ./app/static

# Set up virtual environment
echo "Creating python virtual environment..."
virtualenv --quiet venv
./venv/bin/pip install --quiet -r requirements.txt

# install gunicorn
./venv/bin/pip install gunicorn

# Copy systemd files
echo "Configuring systemd services..."
cp ./example-confs/oee_celery_beat.service /etc/systemd/system
cp ./example-confs/oee_server.service /etc/systemd/system
cp ./example-confs/oee_discovery.service /etc/systemd/system
cp ./example-confs/oee_celery.service /etc/systemd/system

# Edit default values (user, working directory) in example systemd files
sed -i 's&(USERNAME)&'$USER'&g' /etc/systemd/system/oee_server.service /etc/systemd/system/oee_celery.service /etc/systemd/system/oee_celery_beat.service /etc/systemd/system/oee_discovery.service
sed -i 's&/home/user/oee_server&'$PWD'&g' /etc/systemd/system/oee_server.service /etc/systemd/system/oee_celery.service /etc/systemd/system/oee_celery_beat.service /etc/systemd/system/oee_discovery.service

# Enable & start services
systemctl daemon-reload
systemctl enable oee_server oee_discovery oee_celery oee_celery_beat
systemctl start oee_server oee_discovery oee_celery oee_celery_beat

# Set up Nginx
echo "Setting up Nginx..."
unlink /etc/nginx/sites-enabled/default
cp ./example-confs/nginx-conf-example /etc/nginx/sites-available
ln -s /etc/nginx/sites-available/nginx-conf-example /etc/nginx/sites-enabled
nginx -t
nginx -s reload
ufw allow 'Nginx Full'

read -p "Complete. Press enter to continue"

