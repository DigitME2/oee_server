# OEE Monitoring Webapp

This project was made to monitor OEE for machines

This constites the central server, which can receive live OEE data from client and is accessed through a flask webapp.



## Documentation

POSTing to /run_schedule causes the machines schedules to be run for that day, and saved to the scheduled_activity
table. It can be ran on a different date by giving it the argument date=dd-mm-yy
e.g. curl -X POST http://localhost:5000/run_schedule?date=18-08-19

This is suggested to be run via crontab
0 1 * * * /usr/bin/curl -X POST http://localhost:8001/run_schedule
