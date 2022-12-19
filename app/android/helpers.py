import logging

from flask import current_app
from sqlalchemy import create_engine, text

from app.default.models import Settings
from config import Config

logger = logging.getLogger('flask.app')


def get_job_start_data(input_type: str, input_autofill) -> dict:
    """ Returns a dict for the data requested at the start of a job,
    allowing the android device to build a start job form.

    For custom validation, a "validation" entry can be added to each data dictionary. This should be a dictionary
    containing the allowed values for the data as keys, with an explanation as values
    e.g. "job_number": {"title": "Job No", ... , "validation": {123: "order-1", 456: "order-2"}}
    Don't send an empty validation list or nothing will be allowed. Omit the validation entry if none required.
    A "warning" key can be sent if retrieval fails, this will be shown to the user underneath the data entry.
    """
    current_settings = Settings.query.get_or_404(1)
    job_start_data = {"job_number": {"title": "Job Number",
                                     "type": current_settings.job_number_input_type,
                                     "autofill": ""},
                      "ideal_cycle_time": {"type": "number",
                                           "autofill": input_autofill}}
    if Config.USE_JOB_VALIDATION:
        try:
            job_start_data["job_number"]["validation"] = get_job_validation_dict()
        except Exception as e:
            job_start_data["job_number"]["warning"] = "Could not get job validation data from database."
            current_app.logger.exception("Failed to get job validation data")
    if current_settings.allow_delayed_job_start:
        job_start_data["start_time"] = {"title": "Start Time",
                                        "type": "time",
                                        "autofill": "current"}
    match input_type:
        case "cycle_time_seconds":
            job_start_data["ideal_cycle_time"]["title"] = f"Ideal cycle time (sec)"

        case "cycle_time_minutes":
            job_start_data["ideal_cycle_time"]["title"] = f"Ideal cycle time (min)"

        case "cycle_time_hours":
            job_start_data["ideal_cycle_time"]["title"] = f"Ideal cycle time (hrs)"

        case "parts_per_second":
            job_start_data["ideal_cycle_time"]["title"] = f"Parts per second"

        case "parts_per_minute":
            job_start_data["ideal_cycle_time"]["title"] = f"Parts per minute"

        case "parts_per_hour":
            job_start_data["ideal_cycle_time"]["title"] = f"Parts per hour"

        case "planned_qty_minutes":
            job_start_data.pop("ideal_cycle_time")
            job_start_data["planned_quantity"] = {"title": "Planned quantity",
                                                  "type": "number",
                                                  "autofill": ""}
            job_start_data["planned_time"] = {"title": "Planned time (min)",
                                              "type": "number",
                                              "autofill": ""}
        case "no_cycle_time":
            del job_start_data["ideal_cycle_time"]

    return job_start_data


def parse_cycle_time(input_type: str, json_data) -> int:
    match input_type:
        case "cycle_time_seconds":
            data_in = float(json_data["ideal_cycle_time"])
            cycle_time_seconds = data_in

        case "cycle_time_minutes":
            data_in = float(json_data["ideal_cycle_time"])
            cycle_time_seconds = data_in * 60

        case "cycle_time_hours":
            data_in = float(json_data["ideal_cycle_time"])
            cycle_time_seconds = data_in * 3600

        case "parts_per_second":
            data_in = float(json_data["ideal_cycle_time"])
            cycle_time_seconds = 1 / data_in

        case "parts_per_minute":
            data_in = float(json_data["ideal_cycle_time"])
            cycle_time_seconds = (1 / data_in) * 60

        case "parts_per_hour":
            data_in = float(json_data["ideal_cycle_time"])
            cycle_time_seconds = (1 / data_in) * 3600

        case "planned_qty_minutes":
            planned_quantity = json_data["planned_quantity"]
            planned_time = json_data["planned_time"]
            cycle_time_seconds = (planned_time * 60) / planned_quantity

        case "no_cycle_time":
            cycle_time_seconds = None

        case _:
            raise TypeError("Could not parse cycle time")
    return cycle_time_seconds


def get_job_validation_dict() -> dict:
    job_numbers = {}
    engine = create_engine(Config.SECOND_DATABASE_ODBC_STRING)
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="SERIALIZABLE")
        with conn.begin():
            sql_query = text(Config.JOB_VALIDATION_SQL_STRING)
            result = engine.execute(sql_query)
            for row in result:
                if len(row) == 2:
                    job_numbers[row[0]] = row[1]
                else:
                    job_numbers[row[0]] = ""
    return job_numbers


REQUESTED_DATA_JOB_END = {"quantity_good": {"title": "Good Qty",
                                            "type": "number",
                                            "autofill": ""},
                          "rejects": {"title": "Rejects Qty",
                                      "type": "number",
                                      "autofill": ""}}
