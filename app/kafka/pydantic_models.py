from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Login(BaseModel):
    action: str = "login"
    user_name: str
    station_name: str
    timestamp: datetime = datetime.now().timestamp()


class Logout(BaseModel):
    action: str = "logout"
    user_name: str
    station_name: str
    timestamp: datetime = datetime.now().timestamp()


class StartJob(BaseModel):
    action: str = "start-job"
    user_name: str
    station_name: Optional[str]
    job_number: str
    ideal_cycle_time_s: int
    timestamp: datetime = datetime.now().timestamp()


class ChangeState(BaseModel):
    action: str = "state-change"
    station_name: str
    new_state: str
    user_name: Optional[str]
    timestamp: datetime = datetime.now().timestamp()


class EndJob(BaseModel):
    action: str = "end-job"
    user_name: str
    station_name: Optional[str]
    job_number: str
    quantity: int
    rejects: int
    timestamp: datetime = datetime.now().timestamp()
