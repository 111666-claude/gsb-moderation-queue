import unittest

from reports.core import Queue


def queue():
    return Queue(escalate_ms=1000, max_pending=10)


class BasicTest(unittest.TestCase):
    def test_empty_pending(self):
        self.assertEqual(queue().pending(0), [])

    def test_report_then_pending(self):
        target = queue()
        target.report("t1", "p1", 0)
        self.assertEqual(target.pending(0), ["t1"])

    def test_reporters_of_unknown_target(self):
        self.assertEqual(queue().reporters("ghost"), 0)

    def test_first_seen_of_unknown_target(self):
        self.assertIsNone(queue().first_seen("ghost"))

    def test_scanned_starts_at_zero(self):
        self.assertEqual(queue().scanned_count(), 0)


if __name__ == "__main__":
    unittest.main()
