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


class MergeTest(unittest.TestCase):
    def test_same_target_merges_into_one_pending(self):
        target = queue()
        target.report("t1", "p1", 0)
        target.report("t1", "p2", 10)
        self.assertEqual(target.pending(20), ["t1"])

    def test_distinct_targets_stay_separate(self):
        target = queue()
        target.report("t1", "p1", 0)
        target.report("t2", "p1", 1)
        self.assertEqual(sorted(target.pending(2)), ["t1", "t2"])


class ReporterDedupTest(unittest.TestCase):
    def test_same_reporter_counts_once(self):
        target = queue()
        target.report("t1", "p1", 0)
        target.report("t1", "p1", 5)
        target.report("t1", "p1", 9)
        self.assertEqual(target.reporters("t1"), 1)

    def test_distinct_reporters_count(self):
        target = queue()
        target.report("t1", "p1", 0)
        target.report("t1", "p2", 1)
        self.assertEqual(target.reporters("t1"), 2)


class PriorityTest(unittest.TestCase):
    def test_more_reporters_first(self):
        target = queue()
        target.report("t1", "p1", 0)
        target.report("t2", "p2", 5)
        target.report("t2", "p3", 6)
        self.assertEqual(target.pending(20)[0], "t2")

    def test_earlier_first_seen_breaks_tie(self):
        target = queue()
        target.report("t1", "p1", 5)
        target.report("t2", "p2", 1)
        self.assertEqual(target.pending(10), ["t2", "t1"])

    def test_target_id_breaks_final_tie(self):
        target = queue()
        target.report("tb", "p1", 0)
        target.report("ta", "p2", 0)
        self.assertEqual(target.pending(10), ["ta", "tb"])


class EscalateTest(unittest.TestCase):
    def test_not_urgent_before_threshold(self):
        target = queue()
        target.report("t1", "p1", 0)
        self.assertFalse(target.urgent("t1", 999))

    def test_urgent_at_threshold(self):
        target = queue()
        target.report("t1", "p1", 0)
        self.assertTrue(target.urgent("t1", 1000))

    def test_urgent_targets_rank_before_normal(self):
        target = queue()
        target.report("t1", "p1", 0)
        target.report("t2", "p2", 1500)
        target.report("t2", "p3", 1501)
        self.assertEqual(target.pending(2000), ["t1", "t2"])

    def test_resolved_target_not_urgent(self):
        target = queue()
        target.report("t1", "p1", 0)
        target.resolve("t1", "r1", 1)
        self.assertFalse(target.urgent("t1", 5000))


class CapTest(unittest.TestCase):
    def test_report_beyond_cap_returns_false(self):
        target = Queue(escalate_ms=1000, max_pending=2)
        self.assertTrue(target.report("t0", "p1", 0))
        self.assertTrue(target.report("t1", "p1", 1))
        self.assertFalse(target.report("t2", "p1", 2))
        self.assertEqual(sorted(target.pending(3)), ["t0", "t1"])

    def test_merge_does_not_consume_cap(self):
        target = Queue(escalate_ms=1000, max_pending=1)
        self.assertTrue(target.report("t0", "p1", 0))
        self.assertTrue(target.report("t0", "p2", 1))
        self.assertFalse(target.report("t1", "p1", 2))


class ResolveTest(unittest.TestCase):
    def test_duplicate_req_id_returns_false(self):
        target = queue()
        target.report("t1", "p1", 0)
        self.assertTrue(target.resolve("t1", "same", 1))
        self.assertFalse(target.resolve("t1", "same", 2))

    def test_resolved_target_leaves_pending(self):
        target = queue()
        target.report("t1", "p1", 0)
        target.report("t2", "p2", 1)
        target.resolve("t1", "r1", 2)
        self.assertEqual(target.pending(3), ["t2"])

    def test_resolve_frees_cap_slot(self):
        target = Queue(escalate_ms=1000, max_pending=1)
        target.report("t0", "p1", 0)
        target.resolve("t0", "r1", 1)
        self.assertTrue(target.report("t1", "p1", 2))


class ScanCostTest(unittest.TestCase):
    def test_scanned_does_not_grow_with_total_reports(self):
        target = Queue(escalate_ms=100000, max_pending=10000)
        for index in range(3000):
            target.report("t1", "p-%d" % index, index)
        for index in range(3000):
            target.pending(index)
        self.assertLessEqual(target.scanned_count(), 6000)

    def test_repeated_sequence_is_deterministic(self):
        def run():
            target = queue()
            target.report("t1", "p1", 0)
            target.report("t1", "p2", 1)
            target.report("t2", "p3", 2)
            first = target.pending(3)
            target.resolve("t1", "r1", 4)
            return first, target.pending(5)

        self.assertEqual(run(), run())
