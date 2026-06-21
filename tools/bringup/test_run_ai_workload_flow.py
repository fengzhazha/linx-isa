#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_ai_workload_flow


class AiWorkloadFlowTests(unittest.TestCase):
    def classify(self, text: str) -> tuple[str, str]:
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "compile.log"
            log_path.write_text(text, encoding="utf-8")
            return run_ai_workload_flow.classify_supernpu_compile_failure(log_path)

    def test_supernpu_missing_linx_tile_api_is_benchmark_owned(self) -> None:
        owner, evidence = self.classify(
            "tileop_api.hpp:59:3: error: use of undeclared identifier 'TAND_Impl'\n"
        )
        self.assertEqual(owner, "benchmark")
        self.assertIn("tile API", evidence)

    def test_supernpu_unsupported_linx_runtime_contract_is_benchmark_owned(self) -> None:
        owner, evidence = self.classify(
            "error: static assertion failed due to requirement "
            "'tile_shape::isBoxedLayout == false': "
            "Linx smoke TCOPYIN supports only unboxed tiles\n"
        )
        self.assertEqual(owner, "benchmark")
        self.assertIn("runtime contract", evidence)

    def test_supernpu_matmul_acc_contract_is_benchmark_owned(self) -> None:
        owner, evidence = self.classify(
            "error: static assertion failed: Linx scalar MATMUL does not support ACC tile operands\n"
        )
        self.assertEqual(owner, "benchmark")
        self.assertIn("runtime contract", evidence)

    def test_supernpu_direct_boot_libc_dependency_is_benchmark_owned(self) -> None:
        owner, evidence = self.classify("ld.lld: error: undefined symbol: malloc\n")
        self.assertEqual(owner, "benchmark")
        self.assertIn("direct-boot runtime", evidence)

    def test_unknown_supernpu_compile_failure_remains_compiler_owned(self) -> None:
        owner, evidence = self.classify("clang++: error: backend crashed unexpectedly\n")
        self.assertEqual(owner, "compiler")
        self.assertEqual(evidence, "SuperNPUBench compile failed")

    def test_case_filter_supports_exact_id_match(self) -> None:
        cases = [
            self.case("supernpu-tileop_api-TSub"),
            self.case("supernpu-tileop_api-TSubs"),
        ]
        selected = run_ai_workload_flow.filter_cases(
            cases, {1}, [], ["=supernpu-tileop_api-TSub"], 0
        )
        self.assertEqual([case.id for case in selected], ["supernpu-tileop_api-TSub"])

    def test_skill_evolve_note_preserves_no_update_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            payload = run_ai_workload_flow.write_skill_doc_evolution(
                Path(td), [], "no-update classifier-only evidence"
            )
        self.assertEqual(
            payload["skill_evolve"],
            "skill-evolve: no-update classifier-only evidence",
        )

    def test_pto_tload_store_catalog_case_has_standalone_harness(self) -> None:
        cases = run_ai_workload_flow.discover_cases(run_ai_workload_flow.repo_root())
        case = next(case for case in cases if case.id == "pto-kernel-tload_store")

        self.assertEqual(case.kind, "pto_kernel")
        self.assertTrue(case.produces_elf)
        self.assertTrue(case.model_eligible)
        self.assertEqual(case.metadata["standalone_harness"], "tload_store_i32")
        self.assertIn("-DPTO_QEMU_SMOKE=1", case.metadata["compile_defines"])

    def test_pto_gemm_catalog_case_has_standalone_harness(self) -> None:
        cases = run_ai_workload_flow.discover_cases(run_ai_workload_flow.repo_root())
        case = next(case for case in cases if case.id == "pto-kernel-gemm")

        self.assertEqual(case.kind, "pto_kernel")
        self.assertTrue(case.produces_elf)
        self.assertTrue(case.model_eligible)
        self.assertEqual(case.metadata["standalone_harness"], "gemm_i32")
        self.assertIn("-DPTO_QEMU_SMOKE=1", case.metadata["compile_defines"])

    def test_other_pto_catalog_cases_remain_compile_static(self) -> None:
        cases = run_ai_workload_flow.discover_cases(run_ai_workload_flow.repo_root())
        case = next(case for case in cases if case.id == "pto-kernel-add_custom")

        self.assertEqual(case.kind, "pto_kernel")
        self.assertFalse(case.produces_elf)
        self.assertFalse(case.model_eligible)
        self.assertNotIn("standalone_harness", case.metadata)

    def case(self, case_id: str) -> run_ai_workload_flow.Case:
        return run_ai_workload_flow.Case(
            id=case_id,
            kind="supernpu",
            suite="tileop_api",
            tier=1,
            source_paths=[Path(f"{case_id}.cpp")],
            manifest_path=None,
            workdir=Path("."),
            compile_command=None,
            qemu_command=None,
            model_eligible=True,
            produces_elf=True,
            expected="test",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
