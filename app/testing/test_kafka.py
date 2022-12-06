import unittest

from app.kafka import events as kafka_events
from config import Config


class TestKafka(unittest.TestCase):

    def setUp(self) -> None:
        if not Config.ENABLE_KAFKA:
            self.skipTest("Kafka not enabled. Skipping kafka test")

    def test_login(self):
        kafka_events.android_login("test-user", "test-station")

    def test_logout(self):
        kafka_events.android_logout("test-user", "test-station")

    def test_start_job(self):
        kafka_events.start_job("test-job", "test-user", 10)

    def test_end_job(self):
        kafka_events.end_job("test-job", "test-user", 10, 1)

    def test_set_machine(self):
        kafka_events.set_machine_activity("test", "test_machine", "test_user")
