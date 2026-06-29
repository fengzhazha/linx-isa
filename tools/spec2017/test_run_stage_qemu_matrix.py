#!/usr/bin/env python3
from __future__ import annotations

import unittest

import run_stage_qemu_matrix as matrix


class StageQemuMatrixTests(unittest.TestCase):
    def test_multi_run_benchmark_reports_failing_subrun(self) -> None:
        summary = {
            "results": {
                "500.perlbench_r": {
                    "ok": False,
                    "qemu": [
                        {
                            "failure_class": "none",
                            "heartbeat_last_bpc": "0x15555d66f2",
                            "heartbeat_last_count": 34000000001,
                            "heartbeat_last_progress": "site-change",
                            "heartbeat_running": True,
                            "heartbeat_site_progress": True,
                            "log": "run_001/qemu.log",
                        },
                        {
                            "failure_class": "user-trap",
                            "failure_evidence": "LINX_USER_TRAP addr=0x3f7fee56880000",
                            "heartbeat_last_bpc": "0x1555677c50",
                            "heartbeat_last_count": 4000000025,
                            "heartbeat_last_progress": "site-change",
                            "heartbeat_running": True,
                            "heartbeat_site_progress": True,
                            "log": "run_002/qemu.log",
                        },
                    ],
                },
                "999.specrand_ir": {
                    "ok": True,
                    "qemu": [{"failure_class": "none"}],
                },
            }
        }

        self.assertEqual(
            matrix._transport_failure_classes(summary),
            {"500.perlbench_r": "user-trap"},
        )
        self.assertEqual(
            matrix._transport_failure_details(summary)["500.perlbench_r"]["log"],
            "run_002/qemu.log",
        )
        self.assertEqual(
            matrix._transport_failure_details(summary)["500.perlbench_r"][
                "heartbeat_last_bpc"
            ],
            "0x1555677c50",
        )


if __name__ == "__main__":
    unittest.main()
