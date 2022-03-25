import unittest
from datetime import datetime, time, timedelta

from app.testing.base import BaseTest
from app.visualisation.graphs import create_machine_gantt, create_multiple_machines_gantt, create_schedules_gantt, \
    create_oee_line


class VisualisationTest(BaseTest):

    def test_graphs(self):
        with self.app.app_context():
            day_start = datetime.combine(date=datetime.now().date(), time=time(hour=0, minute=0, second=0, microsecond=0))
            day_end = day_start + timedelta(days=1)
            gantt_graph = create_machine_gantt(machine_id=1, graph_start=day_start, graph_end=day_end)
            self.assertIsNotNone(gantt_graph)
            oee_line_graph = create_oee_line(day_start.date(), day_end.date(), [1])
            self.assertIsNotNone(oee_line_graph)
            multiple_gantt_graph = create_multiple_machines_gantt(graph_start=day_start, graph_end=day_end, machine_ids=[1])
            self.assertIsNotNone(multiple_gantt_graph)
            schedules_gantt = create_schedules_gantt(graph_start=day_start, graph_end=day_end, machine_ids=[1])
            self.assertIsNotNone(schedules_gantt)


if __name__ == '__main__':
    unittest.main()
