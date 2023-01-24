import logging
import threading

from app.extensions import kafka_producer as producer
from app.kafka.pydantic_models import Logout, StartJob, Login, EndJob, ChangeState

USER_ACTIVITY_TOPIC = "user-activity"
JOB_ACTIVITY_TOPIC = "job-activity"
MACHINE_ACTIVITY_TOPIC = "machine-activity"

logging.getLogger('kafka').setLevel(logging.WARNING)


class BackgroundKafkaPublish(threading.Thread):
    """ A simple background task to publish a kafka message"""
    def __init__(self, topic: str, message: bytes):
        super().__init__()
        self.topic = topic
        self.msg = message

    def run(self, *args, **kwargs):
        producer.send(self.topic, self.msg)


def android_login(user_name, station_name):
    """ Publish a Kafka message for a user login"""
    msg = Login(user_name=user_name, station_name=station_name)
    publish_task = BackgroundKafkaPublish(USER_ACTIVITY_TOPIC, msg.json().encode("utf-8"))
    publish_task.start()


def android_logout(user_name, machine_name):
    """ Publish a Kafka message for a user logout"""
    msg = Logout(user_name=user_name, station_name=machine_name)
    publish_task = BackgroundKafkaPublish(USER_ACTIVITY_TOPIC, msg.json().encode("utf-8"))
    publish_task.start()


def start_job(job_number, user_name, ideal_cycle_time_s):
    """ Publish a Kafka message for a job start"""
    msg = StartJob(job_number=job_number, user_name=user_name, ideal_cycle_time_s=ideal_cycle_time_s)
    publish_task = BackgroundKafkaPublish(JOB_ACTIVITY_TOPIC, msg.json().encode("utf-8"))
    publish_task.start()


def end_job(job_number, user_name):
    """ Publish a Kafka message for a job end"""
    msg = EndJob(job_number=job_number, user_name=user_name)
    publish_task = BackgroundKafkaPublish(JOB_ACTIVITY_TOPIC, msg.json().encode("utf-8"))
    publish_task.start()


def set_machine_activity(new_activity_name, machine_name, user_name):
    """ Publish a Kafka message for a machine changing state"""
    msg = ChangeState(new_state=new_activity_name, station_name=machine_name, user_name=user_name)
    publish_task = BackgroundKafkaPublish(MACHINE_ACTIVITY_TOPIC, msg.json().encode("utf-8"))
    publish_task.start()
