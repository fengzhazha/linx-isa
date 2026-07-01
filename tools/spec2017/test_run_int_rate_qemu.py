#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
from pathlib import Path
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

    def test_child_sigkill_is_classified(self) -> None:
        result = runner._classify_qemu_result(
            text=(
                "LINX_SPEC_DBG wait wr=13 errno=0 waitid_errno=0 method=7 "
                "fallback=0 status=0x0000000000000009 exited=0 code=-1 "
                "signaled=1 sig=9\n"
                "LINX_SPEC_FAIL child-exit\n"
            ),
            timed_out=False,
            stalled=False,
            panic_seen=False,
            fail_marker=True,
        )

        self.assertEqual(result["class"], "spec-child-sigkill")
        self.assertIn("sig=9", result["evidence"])

    def test_child_sigkill_with_oom_is_classified(self) -> None:
        result = runner._classify_qemu_result(
            text=(
                "oom_kill 0\n"
                "oom_kill 1\n"
                "LINX_SPEC_DBG wait wr=13 errno=0 waitid_errno=0 method=7 "
                "fallback=0 status=0x0000000000000009 exited=0 code=-1 "
                "signaled=1 sig=9\n"
                "LINX_SPEC_FAIL child-exit\n"
            ),
            timed_out=False,
            stalled=False,
            panic_seen=False,
            fail_marker=True,
        )

        self.assertEqual(result["class"], "spec-child-sigkill-oom")
        self.assertIn("oom_kill=1", result["evidence"])

    def test_child_sigsegv_is_classified(self) -> None:
        result = runner._classify_qemu_result(
            text=(
                "LINX_SPEC_DBG wait wr=13 errno=0 waitid_errno=0 method=7 "
                "fallback=0 status=0x000000000000000b exited=0 code=-1 "
                "signaled=1 sig=11\n"
                "LINX_SPEC_FAIL child-exit\n"
            ),
            timed_out=False,
            stalled=False,
            panic_seen=False,
            fail_marker=True,
        )

        self.assertEqual(result["class"], "spec-child-sigsegv")
        self.assertIn("sig=11", result["evidence"])

    def test_guest_proc_diagnostics_block_dumps_memory_state(self) -> None:
        block = runner._guest_proc_diagnostics_block()

        self.assertIn("/proc/%lld/status", block)
        self.assertIn("LINX_SPEC_CHILD_STATUS_BEGIN", block)
        self.assertIn("LINX_SPEC_MEMINFO_BEGIN", block)
        self.assertIn("LINX_SPEC_VMSTAT_BEGIN", block)
        self.assertIn("LINX_SPEC_PRESSURE_MEMORY_OPEN_FAIL", block)

    def test_qemu_fault_trace_regs_env_enables_trace(self) -> None:
        env: dict[str, str] = {}
        runner._apply_qemu_debug_env(
            env,
            qemu_heartbeat_interval=100,
            qemu_fault_trace_regs=True,
            qemu_fault_trace_limit=3,
        )

        self.assertEqual(env["LINX_HEARTBEAT_INTERVAL"], "100")
        self.assertEqual(env["LINX_QEMU_FAULT_TRACE"], "1")
        self.assertEqual(env["LINX_QEMU_FAULT_TRACE_REGS"], "1")
        self.assertEqual(env["LINX_QEMU_FAULT_TRACE_LIMIT"], "3")

    def test_qemu_fault_trace_filters_env_enable_trace(self) -> None:
        env: dict[str, str] = {}
        runner._apply_qemu_debug_env(
            env,
            qemu_heartbeat_interval=0,
            qemu_fault_trace_regs=False,
            qemu_fault_trace_limit=7,
            qemu_fault_trace_filters={
                "LINX_QEMU_FAULT_TRACE_PC_LO": "0x15559efe00",
                "LINX_QEMU_FAULT_TRACE_PC_HI": "0x15559efe40",
                "LINX_QEMU_FAULT_TRACE_TRAPNUM": "5",
            },
        )

        self.assertEqual(env["LINX_QEMU_FAULT_TRACE"], "1")
        self.assertNotIn("LINX_QEMU_FAULT_TRACE_REGS", env)
        self.assertEqual(env["LINX_QEMU_FAULT_TRACE_LIMIT"], "7")
        self.assertEqual(env["LINX_QEMU_FAULT_TRACE_PC_LO"], "0x15559efe00")
        self.assertEqual(env["LINX_QEMU_FAULT_TRACE_PC_HI"], "0x15559efe40")
        self.assertEqual(env["LINX_QEMU_FAULT_TRACE_TRAPNUM"], "5")

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

    def test_pc_watch_does_not_mask_spec_child_exit(self) -> None:
        result = runner._classify_qemu_result(
            text=(
                "linx_pc_watch: pc=0x155604f424 hit=1 count=42 bpc=0x155604f414\n"
                "LINX_SPEC_DBG wait wr=13 errno=0 waitid_errno=0 method=6 "
                "fallback=0 status=0x0000000000000400 exited=1 code=4 "
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
        self.assertIn("code=4", result["evidence"])

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

    def test_strict_hash_pass_suppresses_specdiff_false_red(self) -> None:
        qemu_runs = [{"failure_class": "none", "failure_evidence": ""}]
        specdiff_info = {
            "ok": False,
            "strict_hash": True,
            "hash_checks": [{"ok": True, "output_name": "suns.out"}],
            "checks": [{"ok": False, "out": "suns.out", "returncode": 2}],
        }

        runner._annotate_specdiff_mismatch(qemu_runs, specdiff_info)

        self.assertTrue(runner._strict_hash_checks_ok(specdiff_info))
        self.assertEqual(qemu_runs[0]["failure_class"], "none")
        self.assertEqual(qemu_runs[0]["failure_evidence"], "")

    def test_indexed_argv_override_targets_requested_argument(self) -> None:
        with mock.patch.dict(os.environ, {"LINX_SPEC_ARGV1_OVERRIDE": "/spec-run/test.txt"}, clear=True):
            argv = runner._apply_argv_overrides(["./bench", "test.txt"])

        self.assertEqual(argv, ["./bench", "/spec-run/test.txt"])

    def test_indexed_argv_override_leaves_unset_arguments_unchanged(self) -> None:
        with mock.patch.dict(os.environ, {"LINX_SPEC_ARGV2_OVERRIDE": "patched"}, clear=True):
            argv = runner._apply_argv_overrides(["./bench", "input", "old"])

        self.assertEqual(argv, ["./bench", "input", "patched"])

    def test_gcc_run_verifies_generated_assembly_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bench_root = Path(td)
            control = bench_root / "data" / "test" / "input" / "control"
            control.parent.mkdir(parents=True)
            control.write_text("t1.c -O3 -finline-limit=50000\n", encoding="utf-8")

            runs = runner._runs_gcc(bench_root, "test", "cpugcc_r_base.mytest-m64")

        self.assertEqual(len(runs), 1)
        self.assertEqual(
            runs[0]["argv"],
            [
                "./cpugcc_r_base.mytest-m64",
                "t1.c",
                "-O3",
                "-finline-limit=50000",
                "-o",
                "t1.opts-O3_-finline-limit_50000.s",
            ],
        )
        self.assertEqual(runs[0]["stdout"], "t1.opts-O3_-finline-limit_50000.out")
        self.assertEqual(runs[0]["verify_outputs"], ["t1.opts-O3_-finline-limit_50000.s"])

    def test_perlbench_train_uses_shared_scripts_and_side_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bench_root = Path(td)
            all_input = bench_root / "data" / "all" / "input"
            train_input = bench_root / "data" / "train" / "input"
            train_output = bench_root / "data" / "train" / "output"
            all_input.mkdir(parents=True)
            train_input.mkdir(parents=True)
            train_output.mkdir(parents=True)

            (all_input / "diffmail.pl").write_text("", encoding="utf-8")
            (all_input / "splitmail.pl").write_text("", encoding="utf-8")
            (train_input / "diffmail.in").write_text("2 550 15 24 23 100\n", encoding="utf-8")
            (train_input / "splitmail.in").write_text("535 13 25 24 1091 1\n", encoding="utf-8")
            (train_input / "perfect.pl").write_text("", encoding="utf-8")
            (train_input / "perfect.in").write_text("b 3\n", encoding="utf-8")
            (train_input / "scrabbl.pl").write_text("", encoding="utf-8")
            (train_input / "scrabbl.in").write_text("letters\n", encoding="utf-8")
            (train_input / "suns.pl").write_text("", encoding="utf-8")
            (train_output / "validate").write_text("", encoding="utf-8")

            runs = runner._runs_perlbench(bench_root, "train", "perlbench_r_base.mytest-m64")

        self.assertEqual([run["stdout"] for run in runs], [
            "diffmail.2.550.15.24.23.100.out",
            "perfect.b.3.out",
            "scrabbl.out",
            "splitmail.535.13.25.24.1091.1.out",
            "suns.out",
        ])
        self.assertEqual(runs[0]["argv"], [
            "./perlbench_r_base.mytest-m64",
            "-I./lib",
            "diffmail.pl",
            "2",
            "550",
            "15",
            "24",
            "23",
            "100",
        ])
        self.assertEqual(runs[3]["argv"][2], "splitmail.pl")
        self.assertEqual(runs[4]["verify_outputs"], ["suns.out", "validate"])

    def test_overlay_input_set_applies_shared_inputs_before_selected_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bench_root = Path(td) / "bench"
            dst_run = Path(td) / "run"
            all_input = bench_root / "data" / "all" / "input"
            train_input = bench_root / "data" / "train" / "input"
            all_input.mkdir(parents=True)
            train_input.mkdir(parents=True)
            dst_run.mkdir()

            (all_input / "shared.pl").write_text("all", encoding="utf-8")
            (all_input / "lib").mkdir()
            (all_input / "lib" / "helper.pm").write_text("lib", encoding="utf-8")
            (train_input / "shared.pl").write_text("train", encoding="utf-8")
            (train_input / "train.in").write_text("input", encoding="utf-8")

            runner._overlay_input_set(bench_root, dst_run, "train")

            self.assertEqual((dst_run / "shared.pl").read_text(encoding="utf-8"), "train")
            self.assertEqual((dst_run / "lib" / "helper.pm").read_text(encoding="utf-8"), "lib")
            self.assertEqual((dst_run / "train.in").read_text(encoding="utf-8"), "input")

    def test_select_run_indices_keeps_matching_compares(self) -> None:
        cfg = {
            "runs": [
                {"argv": ["./b", "a.c"], "verify_outputs": ["a.s"]},
                {"argv": ["./b", "b.c"], "verify_outputs": ["b.s"]},
                {"argv": ["./b", "c.c"], "verify_outputs": ["c.s"]},
            ],
            "compares": [
                {"out": "a.s"},
                {"out": "b.s"},
                {"out": "c.s"},
                {"out": "unrelated.s"},
            ],
        }

        selected = runner._select_run_indices(cfg, [2])

        self.assertEqual(len(selected["runs"]), 1)
        self.assertEqual(selected["runs"][0]["argv"], ["./b", "b.c"])
        self.assertEqual(selected["runs"][0]["source_run_index"], 2)
        self.assertEqual(selected["compares"], [{"out": "b.s"}])
        self.assertEqual(selected["selected_run_indices"], [2])

    def test_select_run_indices_rejects_out_of_range(self) -> None:
        cfg = {
            "runs": [{"argv": ["./b", "a.c"], "verify_outputs": ["a.s"]}],
            "compares": [{"out": "a.s"}],
        }

        with self.assertRaises(SystemExit):
            runner._select_run_indices(cfg, [2])

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
