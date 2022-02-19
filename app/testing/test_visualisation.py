import unittest
from datetime import datetime, time, timedelta

from app import create_app, db
from app.default.models import Machine
from app.setup_database import setup_database
from app.visualisation.graphs import create_machine_gantt


class VisualisationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        with self.app.app_context():
            db.create_all()
            setup_database()

    def test_graphs(self):
        with self.app.app_context():
            day_start = datetime.combine(date=datetime.now().date(), time=time(hour=0, minute=0, second=0, microsecond=0))
            day_end = day_start + timedelta(days=1)
            graph = create_machine_gantt(machine_id=1, graph_start=day_start, graph_end=day_end)
            self.assertIsNotNone(graph)


if __name__ == '__main__':
    unittest.main()
