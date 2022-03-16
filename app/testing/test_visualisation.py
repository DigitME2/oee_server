import unittest
from datetime import datetime, time, timedelta

from app.testing.base import BaseTest
from app.visualisation.graphs import create_machine_gantt


class VisualisationTest(BaseTest):

    def test_graphs(self):
        with self.app.app_context():
            day_start = datetime.combine(date=datetime.now().date(), time=time(hour=0, minute=0, second=0, microsecond=0))
            day_end = day_start + timedelta(days=1)
            graph = create_machine_gantt(machine_id=1, graph_start=day_start, graph_end=day_end)
            self.assertIsNotNone(graph)


if __name__ == '__main__':
    unittest.main()
