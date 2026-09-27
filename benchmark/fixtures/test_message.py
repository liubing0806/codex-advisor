import unittest

from message import message


class MessageTest(unittest.TestCase):
    def test_ready(self):
        self.assertEqual(message(), 'ready')
