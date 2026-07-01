#!/usr/bin/env python3
from __future__ import annotations

import os
import unittest
from unittest import mock

import run_int_rate_qemu as runner


class RunIntRateQemuTests(unittest.TestCase):
    def test_9p_append_enables_storage_init_by_default(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            append = runner._build_kernel_append("9p", "norandmaps")

        self.assertIn("norandmaps", append)
        self.assertIn("linx_storage_init=1", append)

    def test_9p_append_preserves_explicit_storage_init_override(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            append = runner._build_kernel_append("9p", "norandmaps linx_storage_init=0")

        self.assertIn("linx_storage_init=0", append)
        self.assertNotIn("linx_storage_init=1", append)

    def test_9p_force_virtio_mmio_preserves_custom_device_arg(self) -> None:
        with mock.patch.dict(os.environ, {"LINX_SPEC_9P_FORCE_VIRTIO_MMIO": "1"}, clear=True):
            append = runner._build_kernel_append(
                "9p", "virtio_mmio.device=0x100@0x30002000:2"
            )

        self.assertIn("virtio_mmio.device=0x100@0x30002000:2", append)
        self.assertNotIn("virtio_mmio.device=0x200@0x30001000:1", append)

    def test_child_exit_failure_evidence_includes_wait_status(self) -> None:
        result = runner._classify_qemu_result(
            text=(
                "LINX_SPEC_DBG wait wr=13 errno=0 waitid_errno=0 method=0 "
                "fallback=0 status=0x0000000000000100 exited=1 code=1 "
                "signaled=0 sig=-1\n"
                "LINX_SPEC_FAIL child-exit\n"
            ),
            timed_out=False,
            stalled=False,
            panic_seen=False,
            fail_marker=True,
        )

        self.assertEqual(result["class"], "spec-wrapper-fail")
        self.assertIn("LINX_SPEC_FAIL child-exit", result["evidence"])
        self.assertIn("code=1", result["evidence"])
        self.assertIn("signaled=0", result["evidence"])

    def test_chdir_failure_evidence_includes_9p_errno(self) -> None:
        result = runner._classify_qemu_result(
            text=(
                "LINX_SPEC_START 525.x264_r\n"
                "LINX_SPEC_WARN 9p-mount-failed raw_rc=-71 neg_errno=71\n"
                "LINX_SPEC_FAIL chdir-rundir\n"
            ),
            timed_out=False,
            stalled=False,
            panic_seen=False,
            fail_marker=True,
        )

        self.assertEqual(result["class"], "spec-wrapper-fail")
        self.assertIn("LINX_SPEC_FAIL chdir-rundir", result["evidence"])
        self.assertIn("neg_errno=71", result["evidence"])

    def test_pc_watch_exit_is_classified(self) -> None:
        result = runner._classify_qemu_result(
            text=(
                "LINX_HEARTBEAT count=1 pc=0x0 bpc=0x0\n"
                "linx_pc_watch: pc=0xffffffff80001574 hit=1 count=42 bpc=0xffffffff80402128\n"
            ),
            timed_out=False,
            stalled=False,
            panic_seen=False,
            fail_marker=False,
        )

        self.assertEqual(result["class"], "pc-watch-exit")
        self.assertIn("0xffffffff80001574", result["evidence"])

    def test_hash_mismatch_annotates_none_qemu_result(self) -> None:
        qemu_info = {"failure_class": "none", "failure_evidence": ""}
        runner._annotate_hash_mismatch(
            qemu_info,
            {
                "ok": False,
                "checks": [
                    {
                        "ok": False,
                        "output_name": "train.out",
                        "actual_hash": "0x1",
                        "expected_hash": "0x2",
                        "actual_size": 4,
                        "expected_size": 8,
                    }
                ],
            },
        )

        self.assertEqual(qemu_info["failure_class"], "hash-mismatch")
        self.assertIn("train.out", qemu_info["failure_evidence"])
        self.assertIn("0x1", qemu_info["failure_evidence"])
        self.assertIn("0x2", qemu_info["failure_evidence"])

    def test_hash_mismatch_preserves_runtime_failure_class(self) -> None:
        qemu_info = {"failure_class": "user-trap", "failure_evidence": "trap"}
        runner._annotate_hash_mismatch(qemu_info, {"ok": False, "checks": []})

        self.assertEqual(qemu_info["failure_class"], "user-trap")
        self.assertEqual(qemu_info["failure_evidence"], "trap")

    def test_indexed_argv_override_targets_requested_argument(self) -> None:
        with mock.patch.dict(os.environ, {"LINX_SPEC_ARGV1_OVERRIDE": "/spec-run/test.txt"}, clear=True):
            argv = runner._apply_argv_overrides(["./bench", "test.txt"])

        self.assertEqual(argv, ["./bench", "/spec-run/test.txt"])

    def test_indexed_argv_override_leaves_unset_arguments_unchanged(self) -> None:
        with mock.patch.dict(os.environ, {"LINX_SPEC_ARGV2_OVERRIDE": "patched"}, clear=True):
            argv = runner._apply_argv_overrides(["./bench", "input", "old"])

        self.assertEqual(argv, ["./bench", "input", "patched"])

    def test_heartbeat_kernel_addresses_keep_recent_kernel_sites(self) -> None:
        text = "\n".join(
            [
                "LINX_HEARTBEAT count=1 pc=0x1555555000 bpc=0x1555554000 ra=0x0",
                (
                    "LINX_HEARTBEAT count=2 pc=0xffffffff803e88f6 "
                    "bpc=0xffffffff803e88b0 envpc=0xffffffff803e88aa "
                    "ra=0xffffffff800019bc tpc=0x0"
                ),
                (
                    "LINX_HEARTBEAT count=3 pc=0xffffffff803e88f6 "
                    "bpc=0xffffffff803e88b0 envpc=0xffffffff803e88aa "
                    "ra=0xffffffff800019bc tpc=0x0"
                ),
            ]
        )

        self.assertEqual(
            runner._heartbeat_kernel_addresses(text),
            [
                "0xffffffff803e88f6",
                "0xffffffff803e88b0",
                "0xffffffff803e88aa",
                "0xffffffff800019bc",
            ],
        )

    def test_kernel_symbols_suggest_panic_loop_from_panic_source(self) -> None:
        self.assertTrue(
            runner._kernel_symbols_suggest_panic_loop(
                [
                    {"address": "0xffffffff803e88f6", "function": "udelay", "source": "??:0"},
                    {"address": "0xffffffff800019bc", "function": ".LBB14_51", "source": "panic.c:0"},
                ]
            )
        )
        self.assertFalse(
            runner._kernel_symbols_suggest_panic_loop(
                [
                    {"address": "0xffffffff800fb6e2", "function": "kcsan_atomic_next", "source": "page_alloc.c:0"},
                ]
            )
        )


if __name__ == "__main__":
    unittest.main()
