import unittest

from app.testing.base import BaseTest


class DocumentationTest(BaseTest):

    def test_routes(self):
        for route in ["/help", "/help/admin", "/help/data", '/help/android']:
            response = self.test_client.get(route)
            self.assertEqual(response.status_code, 200)  # add assertion here


if __name__ == '__main__':
    unittest.main()
