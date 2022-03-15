from datetime import datetime

from app.default.db_helpers import get_machines_last_job


def get_machines_last_wo_number(machine_id):
    last_job = get_machines_last_job(machine_id)
    return last_job.wo_number


def time_autofill():
    return datetime.now().strftime("HH:mm")


def get_job_start_data(input_type: str) -> dict:
    job_start_data = {"wo_number": {"title": "Job Number",
                                    "type": "number",
                                    "autofill": ""},
                      "ideal_cycle_time": {"type": "number",
                                           "autofill": ""}}
    if input_type == "cycle_time_seconds":
        job_start_data["ideal_cycle_time"]["title"] = f"Ideal cycle time (sec)"

    elif input_type == "cycle_time_minutes":
        job_start_data["ideal_cycle_time"]["title"] = f"Ideal cycle time (min)"

    elif input_type == "cycle_time_hours":
        job_start_data["ideal_cycle_time"]["title"] = f"Ideal cycle time (hrs)"

    elif input_type == "parts_per_second":
        job_start_data["ideal_cycle_time"]["title"] = f"Parts per second"

    elif input_type == "parts_per_minute":
        job_start_data["ideal_cycle_time"]["title"] = f"Parts per minute"

    elif input_type == "parts_per_hour":
        job_start_data["ideal_cycle_time"]["title"] = f"Parts per hour"

    elif input_type == "planned_qty_minutes":
        job_start_data.pop("ideal_cycle_time")
        job_start_data["planned_quantity"] = {"title": "Planned quantity",
                                              "type": "number",
                                              "autofill": ""}
        job_start_data["planned_time"] = {"title": "Planned time (min)",
                                          "type": "number",
                                          "autofill": ""}
    return job_start_data


def parse_cycle_time(input_type: str, json_data) -> int:

    if input_type == "cycle_time_seconds":
        data_in = float(json_data["ideal_cycle_time"])
        cycle_time_seconds = data_in

    elif input_type == "cycle_time_minutes":
        data_in = float(json_data["ideal_cycle_time"])
        cycle_time_seconds = data_in * 60

    elif input_type == "cycle_time_hours":
        data_in = float(json_data["ideal_cycle_time"])
        cycle_time_seconds = data_in * 3600

    elif input_type == "parts_per_second":
        data_in = float(json_data["ideal_cycle_time"])
        cycle_time_seconds = 1 / data_in

    elif input_type == "parts_per_minute":
        data_in = float(json_data["ideal_cycle_time"])
        cycle_time_seconds = (1 / data_in) * 60

    elif input_type == "parts_per_hour":
        data_in = float(json_data["ideal_cycle_time"])
        cycle_time_seconds = (1 / data_in) * 3600

    elif input_type == "planned_qty_minutes":
        planned_quantity = json_data["planned_quantity"]
        planned_time = json_data["planned_time"]
        cycle_time_seconds = (planned_time * 60) / planned_quantity

    else:
        raise TypeError("Could not parse cycle time")
    return cycle_time_seconds


REQUESTED_DATA_JOB_END = {"quantity_produced": {"title": "Quantity Produced",
                                                "type": "number",
                                                "autofill": ""},
                          "rejects": {"title": "Rejects",
                                      "type": "number",
                                      "autofill": ""}}

