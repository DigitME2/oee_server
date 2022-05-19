import unittest
from datetime import datetime, timedelta

from flask_table import Table

from app.testing.base import BaseTest
from app.visualisation.tables import get_oee_table


class TablesTest(BaseTest):
    def test_oee_table(self):
        with self.app.app_context():
            start_date = (datetime.now() - timedelta(days=5)).date()
            end_date = (datetime.now() - timedelta(days=1)).date()
            table = get_oee_table(start_date=start_date, end_date=end_date)
            assert table is not None

    def test_match(self):
        t = Table("test")
        match t:
            case t if isinstance(t, Table):
                print("1")
            case t if isinstance(t, BaseTest):
                print("2")

        assert isinstance(t, Table)


if __name__ == '__main__':
    unittest.main()
