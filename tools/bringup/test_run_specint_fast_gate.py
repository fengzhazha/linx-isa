#!/usr/bin/env python3
from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_specint_fast_gate as gate


class SpecintFastGateTests(unittest.TestCase):
    def test_all_suite_routes_large_payload_bench_to_9p(self) -> None:
        units = gate._suite_execution_units(gate.SUITES["test-all"], "")

        self.assertEqual([unit.name for unit in units], ["test-all", "test-all-large-9p"])
        self.assertEqual(units[0].transports, "initramfs")
        self.assertNotIn("525.x264_r", units[0].benches)
        self.assertEqual(units[1].transports, "9p")
        self.assertEqual(units[1].benches, ("525.x264_r",))

    def test_explicit_transport_override_keeps_suite_unsplit(self) -> None:
        units = gate._suite_execution_units(gate.SUITES["test-all"], "initramfs")

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].name, "test-all")
        self.assertEqual(units[0].transports, "initramfs")
        self.assertIn("525.x264_r", units[0].benches)

    def test_9p_override_keeps_all_benches_together(self) -> None:
        units = gate._suite_execution_units(gate.SUITES["train-all"], "9p")

        self.assertEqual(len(units), 1)
        self.assertEqual(units[0].name, "train-all")
        self.assertEqual(units[0].transports, "9p")
        self.assertEqual(units[0].benches, gate.SPECINT_STAGE_B_BENCHES)


if __name__ == "__main__":
    unittest.main()
