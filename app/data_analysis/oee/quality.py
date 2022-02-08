from datetime import datetime

def get_machine_quality(machine_id, time_start: datetime, time_end: datetime) -> int:
    """ Calculate the quality of machine output for calculating OEE"""
    return 1