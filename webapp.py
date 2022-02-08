import logging
import os
from app import create_app

# Attempt at profiling, pycharm profiler doesn't work
# from datetime import datetime
# import yappi
# import atexit
#
# # End profiling and save the results into file
# def output_profiler_stats_file():
#     profile_file_name = 'yappi.' + datetime.now().isoformat()
#     func_stats = yappi.get_func_stats()
#     func_stats.save(profile_file_name, type='pstat')
#     yappi.stop()
#     yappi.clear_stats()
#
#
# yappi.start()
# atexit.register(output_profiler_stats_file)


# Create the flask app
app = create_app()

# If run by gunicorn, set the loggers to match the gunicorn loggers (which can be set with --log-level)
if "gunicorn" in os.environ.get("SERVER_SOFTWARE", ""):
    print("Copying Gunicorn logger settings")
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
