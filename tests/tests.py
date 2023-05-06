from utils.filters import parse_time
import unittest
import time
from utils.model import User
from app import db, create_app


class TestDb(unittest.TestCase):

    def setUp(self) -> None:
        app = create_app("test")
        self.db = db
        with app.app_context() as self.context:
            self.context.push()

    def test_user(self):
        self.assertIsNone(User.query.filter_by(id=1).first())
        self.assertEqual([], User.query.all())

    def tearDown(self) -> None:
        self.context.pop()


class TestTime(unittest.TestCase):
    def test_time(self):
        self.assertEqual("አሁን", parse_time(time.time()))
        self.assertEqual("ከ30 ሰከንድ በፊት", parse_time(time.time() - 30))
        self.assertEqual("ከ2 ደቂቃዎች በፊት", parse_time(time.time() - 120))
        self.assertEqual("ከ2 ሰዓታት በፊት", parse_time(time.time() - 2*3600))


if __name__ == '__main__':
    unittest.main()
