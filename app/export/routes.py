import calendar
import os
from datetime import datetime, timedelta

import pandas as pd
from flask import request, send_file, abort, render_template, current_app
from flask_login import login_required
from sqlalchemy import inspect

from app import db
from app.default.models import Job
from app.export import bp
from app.export.helpers import get_temp_filepath, create_users_csv, create_machines_csv
from app.login.models import User


@bp.route('/export', methods=['GET'])
@login_required
def export_home():
    """ Returns the page offering reports for the user to download."""
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    users = User.query.all()
    return render_template('export/export_home.html',
                           tables=table_names,
                           users=users)


@bp.route('/export_report', methods=['GET'])
@login_required
def export_report():
    key_column = request.args.get('keyColumn')
    chart_type = request.args.get('chartType')
    start_date_string = request.args.get('dateStart')
    start_time_string = request.args.get('timeStart')
    end_date_string = request.args.get('dateEnd')
    end_time_string = request.args.get('timeEnd')

    # Abort if any arguments are missing
    if key_column is None or \
            chart_type is None or \
            start_date_string is None or \
            start_time_string is None or \
            end_date_string is None or \
            end_time_string is None:
        abort(400)
    try:
        # Get the values for the start and end time of the graph from the url
        requested_start = datetime.strptime(start_date_string + start_time_string, "%d-%m-%Y%H:%M")
        requested_end = datetime.strptime(end_date_string + end_time_string, "%d-%m-%Y%H:%M")
    except ValueError:
        current_app.logger.error("Error reading times", exc_info=True)
        return "Error reading date or time. Date must be in format DD-MM-YYYY. " \
               "Time must be in the format HH:MM (24 hour)"

    #Get the selected key in the dropdown
    if key_column == "Users":
        file_name = f"Users {start_date_string} to {end_date_string}.csv"
        filepath = create_users_csv(time_start=requested_start.timestamp(),
                                    time_end=requested_end.timestamp())
    elif key_column == "Machines":
        file_name = f"Machines {start_date_string} to {end_date_string}.csv"
        filepath = create_machines_csv(time_start=requested_start.timestamp(),
                                       time_end=requested_end.timestamp())

    else:
        return abort(404)
    return send_file(filename_or_fp=filepath,
                     cache_timeout=-1,
                     as_attachment=True,
                     attachment_filename=file_name)


@bp.route('/export_raw')
def export_raw():
    """ Return a raw table"""
    table = request.args.get("table")
    if table is None:
        abort(404)

    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    if table in table_names:
        statement = f"SELECT * FROM {table};"
        df = pd.read_sql(statement, db.engine)

        filepath = get_temp_filepath(table)
        df.to_csv(filepath)
        new_file_name = table + "-raw.csv"
        return send_file(filename_or_fp=filepath,
                         cache_timeout=-1,
                         as_attachment=True,
                         attachment_filename=new_file_name)
    else:
        abort(404)
