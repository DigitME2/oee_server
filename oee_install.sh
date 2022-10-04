#!/usr/bin/env bash
# Start the commmand in command line
cd ~/
sudo apt update
cd ~/oee_server*
sudo mv ../oee_server* ../oee_server
pwd -P
cd ..
cd ~/oee_server/
cp ~/oee_server/example-confs/config.py.example config.py
# install npm package in /app/static
cd app/static/
sudo apt -y install npm
npm install
# return to oee_server directory
cd ~/oee_server/
# install redis 
sudo apt -y install redis 
# install virtual environment
sudo apt -y install python3-venv 
# create virtual environment venv
python3 -m venv venv
#activate virtual venv
#cd ~/oee_server/venv/bin
# install all packages from requirement file
./venv/bin/pip install -r requirements.txt
# install gunicorn
./venv/bin/pip install gunicorn
#sudo ufw allow 5000

#Deactivate venv
#deactivate
sed -i 's/User=oee/User='$USER'/g' ~/oee_server/example-confs/oee_server.service
sed -i 's/user/'$USER'/g' ~/oee_server/example-confs/oee_server.service
sed -i 's/-'$USER'/-user/g' ~/oee_server/example-confs/oee_server.service
sed -i 's/User=oee/User='$USER'/g' ~/oee_server/example-confs/oee_celery.service
sed -i 's/user/'$USER'/g' ~/oee_server/example-confs/oee_celery.service
sed -i 's/-'$USER'/-user/g' ~/oee_server/example-confs/oee_celery.service
sed -i 's/User=oee/User='$USER'/g' ~/oee_server/example-confs/oee_celery_beat.service
sed -i 's/user/'$USER'/g' ~/oee_server/example-confs/oee_celery_beat.service
sed -i 's/-'$USER'/-user/g' ~/oee_server/example-confs/oee_celery_beat.service
sed -i 's/User=oee/User='$USER'/g' ~/oee_server/example-confs/oee_discovery.service
sed -i 's/user/'$USER'/g' ~/oee_server/example-confs/oee_discovery.service
sed -i 's/-'$USER'/-user/g' ~/oee_server/example-confs/oee_discovery.service
cd ~/
cd ..
cd ..
sudo cp ~/oee_server/example-confs/oee_celery_beat.service /etc/systemd/system
sudo cp ~/oee_server/example-confs/oee_server.service /etc/systemd/system
sudo cp ~/oee_server/example-confs/oee_discovery.service /etc/systemd/system
sudo cp ~/oee_server/example-confs/oee_celery.service /etc/systemd/system
sudo systemctl daemon-reload 
sudo systemctl enable oee_server oee_discovery oee_celery oee_celery_beat
sudo systemctl start oee_server oee_discovery oee_celery oee_celery_beat
sudo apt -y install nginx
sudo unlink /etc/nginx/sites-enabled/default
sudo cp ~/oee_server/example-confs/nginx-conf-example /etc/nginx/sites-available
sudo ln -s /etc/nginx/sites-available/nginx-conf-example /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
sudo ufw allow 'Nginx Full'

