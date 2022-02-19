import unittest

from app import create_app


class DocumentationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        with self.app.app_context():
            self.test_client = self.app.test_client()

    def test_routes(self):
        for route in ["/help", "/help/admin", "/help/data", '/help/android']:
            response = self.test_client.get(route)
            self.assertEqual(response.status_code, 200)  # add assertion here


if __name__ == '__main__':
    unittest.main()
