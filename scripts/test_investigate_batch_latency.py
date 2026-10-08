import unittest
from unittest.mock import patch

from investigate_batch_latency import measure, positive_int, summarize


class MeasurementTests(unittest.TestCase):
    def test_wrong_token_values_are_rejected_even_when_lengths_match(self):
        with self.assertRaisesRegex(RuntimeError, "differs"):
            measure(lambda: [[2, 1]], [[1, 2]])

    def test_validation_and_destruction_are_after_clocks_stop(self):
        events = []

        class Output(list):
            def __ne__(self, other):
                events.append("compare")
                return super().__ne__(other)

            def __del__(self):
                events.append("destroy")

        def wall():
            events.append("wall")
            return 10

        def cpu():
            events.append("cpu")
            return 10

        with patch("investigate_batch_latency.time.perf_counter_ns", side_effect=wall):
            with patch("investigate_batch_latency.time.process_time_ns", side_effect=cpu):
                measure(lambda: Output([[1]]), [[1]])
        self.assertEqual(events, ["wall", "cpu", "cpu", "wall", "compare", "destroy"])

    def test_summary_preserves_outlier_and_uses_even_sample_median(self):
        samples = [{"wall_ms": n, "process_cpu_ms": n * 2} for n in [1, 2, 4, 100]]
        result = summarize(samples)
        self.assertEqual(result["median_ms"], 3)
        self.assertEqual(result["max_ms"], 100)
        self.assertAlmostEqual(result["max_over_median"], 100 / 3)
        self.assertEqual(result["median_process_cpu_ms"], 6)

    def test_zero_workloads_are_rejected(self):
        import argparse

        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")


if __name__ == "__main__":
    unittest.main()
