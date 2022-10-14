# OEE Monitoring Webapp

This software was created to track Overall Equipment Effectiveness (OEE) using Android tablets and IOT devices.

This constitutes the central server, which can receive live OEE data from clients and is accessed through a web browser.

This software is accompanied by an Android app, which connects to the server and takes manual input to set the state of its assigned machine. [The app APK can be downloaded from here.](https://github.com/DigitME2/MachineMonitoring/releases) 

## Setup

The software can be automatically set up by running this command in a terminal in Ubuntu 22.04 (Press Ctrl + Alt + T to open a terminal).

```
bash <(curl -sL https://raw.githubusercontent.com/DigitME2/oee_server/production/install.sh)
```

Enter your password if prompted.

This will download the software and set it to run on startup. The software can be reached by opening a browser and entering "localhost" into the address bar. The default user is "admin" and the default password is "digitme2".
This can also be accessed on another PC on the network by entering the host PC's IP address into the address bar of a browser.

### Manual installation

(Tested on Ubuntu 22.04)

Download the source code from this repository

Create `config.py` in the root folder from `example-confs/config.py.example` and edit config options. Modify the secret key to a random string

Run `npm install` in the `/app/static` directory.

The app uses redis as a Celery broker, which is needed for periodic tasks. Redis can be installed with `sudo apt install redis`. Modify `config.py` if using a non-standard redis setup.

Run `pip install -r requirements.txt` in a virtual environment if necessary.

Change `start.sh` to be executable `chmod 755 start.sh` and run it.
(This requires gunicorn to be installed)

`start.sh` runs 3 processes: The server (using gunicorn), a Celery worker and a Celery beat.

To run at startup, the three processes can be run by systemd. Example configs are provided in the `example-confs` folder. Copy these to `/etc/systemd/system` and run `sudo systemctl daemon-reload` then `sudo systemctl enable oee_server oee_discovery oee_celery oee_celery_beat`. Make sure to edit the paths/user in the service config files.

For security, the app should be run by a different user. For example, create a user called oee `useradd oee` and give them ownership of the OEE app `chown -R oee /home/user/oee_server`. Ensure the app is started by the same user in your systemd service files.

The software ideally uses nginx as a reverse proxy. This can be installed with `sudo apt install nginx`. An example config is included in this repo. In order for the android app to work correctly, the proxy server must pass on the IP address of the android client.

To upgrade the database when updating to a new version, run

`flask db migrate -m "your-migration-message"`

`flask db upgrade`


## Documentation

Help files can be found in the app

## Demo mode

When run with `DEMO_MODE=True` in the `config.py` file, the app will fake inputs. On startup it will backfill missed data. The celery worker will fake inputs as long as the app is running.

## API

An external device can change the state of a machine by posting to /api/change-machine-state. The payload should be in the format {"machine_id": 1, "machine_state": 0}, where state=0 means the machine has gone down and 1 means back up. An activity code can be provided optionally, e.g. "activity_code_id": 1
