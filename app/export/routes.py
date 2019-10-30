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
    """ Creates a file for the user to download."""
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    users = User.query.all()
    return render_template('export/export_home.html',
                           tables=table_names,
                           users=users)


@bp.route('/export_users', methods=['GET'])
@login_required
def export_report():
    if "date" not in request.args:
        abort(404)
    date_string = request.args['date']
    try:
        date = datetime.strptime(date_string, "%d-%m-%Y")
    except ValueError:
        current_app.logger.warn("Error reading date for update", exc_info=True)
        return "Error reading date. Date must be in format DD-MM-YYYY"
    # Get the values for the start and end time of the graph from the url
    day_start = date
    day_end = (date + timedelta(days=1))

    week_start = date - timedelta(days=date.weekday())
    week_end = date + timedelta(days=6)

    month_start = date.replace(day=1)
    month_length = calendar.monthrange(date.year, date.month)[1]
    month_end = month_start + timedelta(days=month_length)

    if "users_daily" in request.args:
        file_name = f"Users {date_string}.csv"
        filepath = create_users_csv(time_start=day_start.timestamp(),
                                    time_end=day_end.timestamp())
    elif "users_weekly" in request.args:
        file_name = f"Users wc {week_start.strftime('%d-%m-%Y')}.csv"
        filepath = create_users_csv(time_start=week_start.timestamp(),
                                    time_end=week_end.timestamp())
    elif "users_monthly" in request.args:
        file_name = f"Users {date.strftime('%B')}.csv"
        filepath = create_users_csv(time_start=month_start.timestamp(),
                                    time_end=month_end.timestamp())
    elif "machines_daily" in request.args:
        file_name = f"Machines {date_string}.csv"
        filepath = create_machines_csv(time_start=day_start.timestamp(),
                                       time_end=day_end.timestamp())
    elif "machines_weekly" in request.args:
        file_name = f"Machines wc {week_start.strftime('%d-%m-%Y')}.csv"
        filepath = create_machines_csv(time_start=week_start.timestamp(),
                                       time_end=week_end.timestamp())
    elif "machines_monthly" in request.args:
        file_name = f"Machines {date.strftime('%B')}.csv"
        filepath = create_machines_csv(time_start=month_start.timestamp(),
                                       time_end=month_end.timestamp())
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
