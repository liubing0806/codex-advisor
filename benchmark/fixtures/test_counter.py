import unittest

from counter import increment


class CounterTest(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(increment(2, 3), 5)

    def test_zero(self):
        self.assertEqual(increment(2, 0), 2)

    def test_negative(self):
        with self.assertRaises(ValueError):
            increment(2, -1)
