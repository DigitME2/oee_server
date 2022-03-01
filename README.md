# OEE Monitoring Webapp

This project was made to monitor OEE for machines

This constitutes the central server, which can receive live OEE data from client and is accessed through a flask webapp.

The app is accompanied by an Android app, which connects to the server and takes manual input to set the state of its assigned machine.


## Setup
(Tested on Ubuntu 20.04)

Create `config.py` in the root folder from `example-confs/config.py.example` and edit config options. Modify the secret key to a random string

Run `npm install` in the `/app/static` directory.

The app uses redis as a Celery broker, which is needed for periodic tasks. Redis can be installed with `sudo apt install redis`. Modify `config.py` if using a non-standard redis setup.

Run `pip install -r requirements.txt` in a virtual environment if necessary.

Change `start.sh` to be executable `chmod 755 start.sh` and run it.
(This requires gunicorn to be installed)

`start.sh` runs 3 processes: The server (using gunicorn), a Celery worker and a Celery beat.

To run at startup, the three processes can be run by systemd. Example configs are provided in the `example-confs` folder. Copy these to `/etc/systemd/system` and run `sudo systemctl daemon-reload` then `sudo systemctl enable oee_server oee_celery oee_celery_beat`. Make sure to edit the paths in the service config files.

The software ideally uses nginx as a reverse proxy. This can be install with `sudo apt install nginx`. An example config is included in this repo. In order for the android app to work correctly, the proxy server must pass on the IP address of the android client.



## Documentation

### Workflow Types

Machines can be assigned different work flows to determine the flow of the display on the android tablet. 
The default workflow has the user log in and go straight to the "start job" screen. Once this is entered, the user sees a screen that allows the current 

## Demo mode

When run with `DEMO_MODE=True` in the `config.py` file, the app will fake inputs. On startup it will backfill missed data. The celery worker will fake inputs as long as the app is running.

## Schedule

In order for OEE to be calculated, each machine needs a schedule of planned uptime and planned downtime. A machine is assigned a schedule, and each day the "scheduled activities" are created and stored for that day. If for some reason the scheduler misses a day, they can be done by POSTing to /run_schedule.
e.g. `curl -X POST http://localhost:5000/run_schedule?date=18-08-19`