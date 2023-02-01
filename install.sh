#!/usr/bin/env bash

# Use sudo here to prompt the password straight away
sudo echo "This script will install the DigitME2 OEE Server."
read -p "Press enter to continue."

# Install requirements
echo "Installing apt packages..."
sudo apt-get update -qqq
sudo apt-get install -qq -y git npm redis virtualenv nginx > /dev/null

echo "Downloading from github..."
git clone https://github.com/DigitME2/oee_server.git ~/oee_server --quiet --branch production --depth=1
cd ~/oee_server

# Copy default config
cp ./example-confs/config.example.py config.py

# Change the secret key to a random string
SECRET_KEY=$(echo $RANDOM | md5sum | head -c 20)
sed -i "s/change-this-secret-key/$SECRET_KEY/g" config.py


# install npm package in /app/static
echo "Running npm install..."
npm --prefix ./app/static install ./app/static

# Set up virtual environment
echo "Creating python virtual environment..."
virtualenv --quiet venv
./venv/bin/pip install --quiet -r requirements.txt

# install gunicorn
./venv/bin/pip install gunicorn

# Set up database
./venv/bin/python3 setup_database.py

# Copy systemd files
echo "Configuring systemd services..."
sudo cp ./example-confs/oee_server.service /etc/systemd/system
sudo cp ./example-confs/oee_discovery.service /etc/systemd/system
sudo cp ./example-confs/oee_scheduler.service /etc/systemd/system

# Edit default values (user, working directory) in example systemd files
sudo sed -i 's&(USERNAME)&'$USER'&g' /etc/systemd/system/oee_server.service /etc/systemd/system/oee_scheduler.service /etc/systemd/system/oee_discovery.service
sudo sed -i 's&/home/user/oee_server&'$PWD'&g' /etc/systemd/system/oee_server.service /etc/systemd/system/oee_scheduler.service /etc/systemd/system/oee_discovery.service

# Enable & start services
sudo systemctl daemon-reload
sudo systemctl enable oee_server oee_discovery oee_scheduler
sudo systemctl start oee_server oee_discovery oee_scheduler

# Set up Nginx
echo "Setting up Nginx..."
sudo unlink /etc/nginx/sites-enabled/default
sudo cp ./example-confs/nginx-conf-example /etc/nginx/sites-available/oee-server
sudo sed -i 's&/home/user/oee_server&'$PWD'&g' /etc/nginx/sites-available/oee-server
sudo ln -s /etc/nginx/sites-available/oee-server /etc/nginx/sites-enabled
sudo nginx -t
sudo nginx -s reload
sudo ufw allow 'Nginx Full'

echo "Installation Finished"
