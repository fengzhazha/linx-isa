#!/usr/bin/env python3
"""Run the AI workload hard-break flow through LLVM, QEMU, and LinxCoreModel."""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qemu_build_paths import default_qemu_binary


PASS_STATUSES = {"pass", "skipped", "not_applicable", "not_run"}
DIGEST_RE = re.compile(r"PTO_DIGEST\s+([A-Za-z0-9_]+)\s+0x([0-9A-Fa-f]+)")
GFSIM_BROB_RE = re.compile(
    r"Retired blocks\s+(?P<blocks>\d+)\.\s+BROB head info:\s+"
    r"(?P<head>.*?\bBPC\s+0x(?P<bpc>[0-9A-Fa-f]+).*?)(?:\n|$)"
)
GFSIM_FINISHER_RE = re.compile(
    r"linx_test_finisher write addr=0x10009000 val=0x(?P<value>[0-9A-Fa-f]+)\s+(?P<status>pass|fail)"
)
GFSIM_ASSERT_RE = re.compile(r"ASSERTION FAILED:\s*(?P<assertion>[^\n]+)")
FORBIDDEN_ASM_RE = re.compile(
    r"((^|[^A-Za-z0-9_])L\.|set_flag|wait_flag|TSync|B\.SET|B\.WAIT)",
    re.IGNORECASE,
)
FINISHER_PASS_LOW8 = 0x55
FINISHER_FAIL_LOW8 = 0x33
FINISHER_RESET_LOW8 = 0x77
LINX_DIRECT_BOOT_LINK_SCRIPT = """ENTRY(_start)
PHDRS {
  text PT_LOAD FLAGS(5);
  data PT_LOAD FLAGS(6);
}
SECTIONS {
  . = 0x00010000;
  .text : { KEEP(*(.text._start)) *(.text*) } :text
  .rodata : { *(.rodata*) *(.eh_frame*) } :text
  . = ALIGN(0x1000);
  .init_array : { *(.init_array*) *(.fini_array*) } :data
  .data : { *(.sdata*) *(.data*) *(.got*) } :data
  .bss (NOLOAD) : { *(.bss*) *(.sbss*) *(.relro_padding*) *(COMMON) } :data
  . = ALIGN(16);
  .bootstack (NOLOAD) : {
    __start_init_stack = .;
    . += 0x4000;
    __end_init_stack = .;
  } :data
}
"""
LINX_MODEL_SMOKE_SOURCE = r"""extern "C" __attribute__((noreturn, section(".text._start"))) void _start(void) {
  __asm__ volatile(
      "BSTART.STD\n"
      "lui 65545, ->u\n"
      "lui 5, ->t\n"
      "addi t#1, 1365, ->t\n"
      "c.swi t#1, [u#1, 0]\n"
      "BSTOP\n"
      ::: "memory");
  while (1) {
    __asm__ volatile("" ::: "memory");
  }
}
"""
SUPER_SMOKE_TESTCASES = {"TAdd", "MatMul"}


@dataclasses.dataclass
class Case:
    id: str
    kind: str
    suite: str
    tier: int
    source_paths: list[Path]
    manifest_path: Path | None
    workdir: Path
    compile_command: str | list[str] | None
    qemu_command: str | list[str] | None
    model_eligible: bool
    produces_elf: bool
    expected: str
    metadata: dict[str, Any]


@dataclasses.dataclass
class CaseState:
    case: Case
    case_dir: Path
    stages: dict[str, dict[str, Any]] = dataclasses.field(default_factory=dict)
    artifacts: dict[str, str] = dataclasses.field(default_factory=dict)
    qemu_digests: dict[str, str] = dataclasses.field(default_factory=dict)
    model_digests: dict[str, str] = dataclasses.field(default_factory=dict)
    failure_stage: str | None = None
    failure_owner: str | None = None
    failure_evidence: str | None = None


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("ai-%Y%m%d-%H%M%S")


def default_flow_path(root: Path) -> Path:
    return root / "docs" / "bringup" / "ai_workload_bringup_flow.json"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def slug(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text.strip())
    text = text.strip("-._")
    return text or "case"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: invalid JSON {path}: {exc}") from exc


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def submodule_sha(root: Path, rel: str) -> str | None:
    path = root / rel
    if not path.exists():
        return None
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def load_flow(path: Path) -> dict[str, Any]:
    data = read_json(path)
    if data.get("schema_version") != 1:
        raise SystemExit(f"error: unsupported flow schema_version in {path}")
    profiles = data.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise SystemExit(f"error: flow has no profiles: {path}")
    stages = data.get("stages")
    if not isinstance(stages, list) or not stages:
        raise SystemExit(f"error: flow has no stages: {path}")
    stage_ids: set[str] = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise SystemExit("error: each stage must be an object")
        stage_id = str(stage.get("id", "")).strip()
        if not stage_id:
            raise SystemExit("error: stage missing id")
        if stage_id in stage_ids:
            raise SystemExit(f"error: duplicate stage id: {stage_id}")
        stage_ids.add(stage_id)
        stage_profiles = stage.get("profiles")
        if not isinstance(stage_profiles, list) or not stage_profiles:
            raise SystemExit(f"error: stage {stage_id} missing profiles")
        invalid = sorted(str(p) for p in stage_profiles if p not in profiles)
        if invalid:
            raise SystemExit(
                f"error: stage {stage_id} has invalid profiles: {', '.join(invalid)}"
            )
    return data


def selected_stages(
    flow: dict[str, Any],
    profile: str,
    requested: list[str],
    start_at: str | None,
    stop_after: str | None,
) -> list[dict[str, Any]]:
    if profile not in flow["profiles"]:
        raise SystemExit(
            "error: invalid --profile "
            f"{profile}; choose one of {', '.join(sorted(flow['profiles']))}"
        )
    stages = [
        stage
        for stage in flow["stages"]
        if profile in {str(p) for p in stage.get("profiles", [])}
    ]
    if requested:
        wanted = set(requested)
        stages = [stage for stage in stages if stage["id"] in wanted]
        missing = sorted(wanted - {stage["id"] for stage in stages})
        if missing:
            raise SystemExit(
                "error: requested stage is not enabled for profile "
                f"{profile}: {', '.join(missing)}"
            )
    if start_at:
        ids = [stage["id"] for stage in stages]
        if start_at not in ids:
            raise SystemExit(f"error: --start-at stage not selected: {start_at}")
        stages = stages[ids.index(start_at) :]
    if stop_after:
        ids = [stage["id"] for stage in stages]
        if stop_after not in ids:
            raise SystemExit(f"error: --stop-after stage not selected: {stop_after}")
        stages = stages[: ids.index(stop_after) + 1]
    return stages


def profile_tiers(flow: dict[str, Any], profile: str, override: list[int]) -> set[int]:
    if override:
        return set(override)
    raw = flow["profiles"][profile].get("tiers", [])
    if not isinstance(raw, list) or not raw:
        raise SystemExit(f"error: profile {profile} has no tier list")
    return {int(t) for t in raw}


def parse_compile_all_line(line: str) -> tuple[str, dict[str, str]] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    parts = [part.strip() for part in stripped.split(";") if part.strip()]
    if not parts:
        return None
    command = parts[-1]
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens or tokens[0] != "make":
        return None
    vars_out: dict[str, str] = {}
    for token in tokens[1:]:
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        vars_out[key] = value
    testcase = vars_out.get("TESTCASE")
    if not testcase:
        return None
    return command, vars_out


def supernpu_tier(suite_rel: str, make_vars: dict[str, str]) -> int:
    testcase = make_vars.get("TESTCASE", "")
    if suite_rel == "tileop_api" and testcase in SUPER_SMOKE_TESTCASES:
        return 0
    if suite_rel.startswith("other/deepseek"):
        return 3
    if suite_rel.startswith("kernel/gemm") or suite_rel.startswith("accelerator/"):
        return 2
    if suite_rel.startswith("kernel/memory") or suite_rel.startswith("kernel/reduction"):
        return 2
    if suite_rel.startswith("kernel/") or "tileop" in suite_rel:
        return 1
    if "py_api" in suite_rel:
        return 3
    return 4


def pto_kernel_tier(rel: str) -> int:
    if "deepseek" in rel:
        return 3
    family = rel.split("/", 1)[0]
    if family in {"memory", "matmul", "elementwise"}:
        return 1
    if family in {"attention", "normalization", "routing", "decode"}:
        return 3
    if family in {"indexing", "layout"}:
        return 2
    return 4


def supernpu_elf_path(root: Path, suite_dir: Path, make_vars: dict[str, str]) -> Path:
    bench_root = root / "workloads" / "SuperNPUBench"
    test_root = bench_root / "test"
    suite_rel = suite_dir.relative_to(test_root).as_posix()
    category_name = suite_rel.replace("/", "_")
    testcase = make_vars["TESTCASE"]
    return bench_root / "output" / suite_rel / "elf" / f"{category_name}_{testcase}_linx.elf"


def supernpu_elf_dir(root: Path, suite_dir: Path) -> Path:
    bench_root = root / "workloads" / "SuperNPUBench"
    test_root = bench_root / "test"
    suite_rel = suite_dir.relative_to(test_root).as_posix()
    return bench_root / "output" / suite_rel / "elf"


def _norm_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def supernpu_source_paths(suite_dir: Path, make_vars: dict[str, str]) -> list[Path]:
    testcase = make_vars["TESTCASE"]
    candidates = [
        suite_dir / "src" / f"{testcase}.cpp",
        suite_dir / testcase / f"{testcase}.cpp",
        suite_dir / f"{testcase}.cpp",
    ]
    for candidate in candidates:
        if candidate.exists():
            return [candidate]

    cpp_files = sorted(suite_dir.rglob("*.cpp"))
    testcase_key = _norm_key(testcase)
    matching = [
        path
        for path in cpp_files
        if _norm_key(path.stem) == testcase_key
        or _norm_key(path.stem) in testcase_key
        or testcase_key in _norm_key(path.stem)
    ]
    if matching:
        return [matching[0]]

    src_dir = suite_dir / "src"
    src_cpp_files = sorted(src_dir.rglob("*.cpp")) if src_dir.exists() else []
    if len(src_cpp_files) == 1:
        return [src_cpp_files[0]]

    return [candidates[0]]


def snapshot_elf_mtimes(elf_dir: Path) -> dict[Path, float]:
    if not elf_dir.exists():
        return {}
    return {path: path.stat().st_mtime for path in elf_dir.glob("*.elf") if path.is_file()}


def find_supernpu_elf_after_compile(
    case: Case,
    root: Path,
    before: dict[Path, float],
    *,
    elf_dir: Path | None = None,
) -> Path | None:
    expected = Path(case.metadata["elf"])
    if elf_dir is not None:
        expected = elf_dir / expected.name
    elif not expected.is_absolute():
        expected = root / expected
    if expected.exists():
        return expected

    if elf_dir is None:
        elf_dir = Path(case.metadata.get("elf_dir", ""))
        if not elf_dir.is_absolute():
            elf_dir = root / elf_dir
    if not elf_dir.exists():
        return None
    candidates = [path for path in elf_dir.glob("*.elf") if path.is_file()]
    if not candidates:
        return None
    produced = [
        path
        for path in candidates
        if path not in before or path.stat().st_mtime > before[path]
    ]
    if produced:
        return max(produced, key=lambda path: path.stat().st_mtime)
    return max(candidates, key=lambda path: path.stat().st_mtime)


def discover_cases(root: Path) -> list[Case]:
    cases: list[Case] = []

    qemu_tests = root / "avs" / "qemu" / "tests"
    cases.append(
        Case(
            id="avs-tile-smoke",
            kind="avs_pto",
            suite="tile",
            tier=0,
            source_paths=[qemu_tests / "10_tile_compile_smoke.cpp"],
            manifest_path=root / "avs" / "qemu" / "run_tests.py",
            workdir=root,
            compile_command=None,
            qemu_command=None,
            model_eligible=True,
            produces_elf=True,
            expected="QEMU PASS marker, then gfsim exit 0",
            metadata={
                "avs_suite": "tile",
                "avs_source_profile": "compile-smoke",
                "description": "PTO tile direct-boot compile-smoke source",
            },
        )
    )
    cases.append(
        Case(
            id="avs-pto-parity",
            kind="avs_pto",
            suite="pto_parity",
            tier=0,
            source_paths=[qemu_tests / "16_pto_kernel_parity.cpp"],
            manifest_path=root / "avs" / "qemu" / "run_tests.py",
            workdir=root,
            compile_command=None,
            qemu_command=None,
            model_eligible=True,
            produces_elf=True,
            expected="PTO_DIGEST parity under QEMU, then gfsim exit 0",
            metadata={"avs_suite": "pto_parity", "description": "PTO kernel parity direct-boot suite"},
        )
    )

    catalog = root / "workloads" / "pto_kernels" / "kernels" / "catalog.txt"
    if catalog.exists():
        for raw in catalog.read_text(encoding="utf-8").splitlines():
            entry = raw.strip()
            if not entry or entry.startswith("#"):
                continue
            source = catalog.parent / entry
            name = Path(entry).stem
            cases.append(
                Case(
                    id=f"pto-kernel-{slug(name)}",
                    kind="pto_kernel",
                    suite=entry.split("/", 1)[0],
                    tier=pto_kernel_tier(entry),
                    source_paths=[source],
                    manifest_path=catalog,
                    workdir=root,
                    compile_command=None,
                    qemu_command=None,
                    model_eligible=False,
                    produces_elf=False,
                    expected="compile/static contract; standalone ELF harness pending",
                    metadata={"catalog_entry": entry},
                )
            )

    bench_root = root / "workloads" / "SuperNPUBench"
    test_root = bench_root / "test"
    if test_root.exists():
        for compile_all in sorted(test_root.rglob("compile.all")):
            suite_dir = compile_all.parent
            suite_rel = suite_dir.relative_to(test_root).as_posix()
            for line_no, line in enumerate(compile_all.read_text(encoding="utf-8").splitlines(), start=1):
                parsed = parse_compile_all_line(line)
                if parsed is None:
                    continue
                command, make_vars = parsed
                testcase = make_vars["TESTCASE"]
                sources = supernpu_source_paths(suite_dir, make_vars)
                case_vars = dict(make_vars)
                case_vars["PLAT"] = "linx"
                case_id = f"supernpu-{slug(suite_rel)}-{slug(testcase)}"
                if len(make_vars) > 1:
                    sig = "-".join(
                        f"{slug(k)}-{slug(v)}"
                        for k, v in sorted(make_vars.items())
                        if k != "TESTCASE"
                    )
                    if sig:
                        case_id = f"{case_id}-{sig}"
                cases.append(
                    Case(
                        id=case_id,
                        kind="supernpu",
                        suite=suite_rel,
                        tier=supernpu_tier(suite_rel, make_vars),
                        source_paths=sources,
                        manifest_path=compile_all,
                        workdir=suite_dir,
                        compile_command=command,
                        qemu_command=None,
                        model_eligible=True,
                        produces_elf=True,
                        expected="SuperNPUBench make/sim pass, then gfsim exit 0",
                        metadata={
                            "compile_all": relpath(root, compile_all),
                            "line": line_no,
                            "make_vars": make_vars,
                            "elf": relpath(root, supernpu_elf_path(root, suite_dir, make_vars)),
                            "elf_dir": relpath(root, supernpu_elf_dir(root, suite_dir)),
                        },
                    )
                )
    return dedupe_cases(cases)


def dedupe_cases(cases: list[Case]) -> list[Case]:
    seen: dict[str, int] = {}
    out: list[Case] = []
    for case in cases:
        base = case.id
        count = seen.get(base, 0)
        seen[base] = count + 1
        if count:
            case.id = f"{base}-{count + 1}"
        out.append(case)
    return out


def filter_cases(
    cases: list[Case],
    tiers: set[int],
    kinds: list[str],
    patterns: list[str],
    limit: int,
) -> list[Case]:
    selected = [case for case in cases if case.tier in tiers]
    if kinds:
        wanted = set(kinds)
        selected = [case for case in selected if case.kind in wanted]
    if patterns:
        selected = [
            case
            for case in selected
            if any(pattern in case.id or pattern in case.suite or pattern in case.kind for pattern in patterns)
        ]
    selected.sort(key=lambda c: (c.tier, c.kind, c.suite, c.id))
    if limit > 0:
        selected = selected[:limit]
    return selected


def tool_paths(root: Path, args: argparse.Namespace) -> dict[str, str]:
    llvm_bin = root / "compiler" / "llvm" / "build-linxisa-clang" / "bin"
    qemu_default = default_qemu_binary(root)
    model_root = Path(args.model_root).expanduser().resolve() if args.model_root else root / "model" / "LinxCoreModel"
    gfsim = Path(args.gfsim).expanduser().resolve() if args.gfsim else model_root / "bin" / "gfsim"
    return {
        "clang": str(Path(args.clang).expanduser().resolve() if args.clang else llvm_bin / "clang"),
        "clangxx": str(Path(args.clangxx).expanduser().resolve() if args.clangxx else llvm_bin / "clang++"),
        "lld": str(Path(args.lld).expanduser().resolve() if args.lld else llvm_bin / "ld.lld"),
        "llvm_objdump": str(
            Path(args.llvm_objdump).expanduser().resolve()
            if args.llvm_objdump
            else llvm_bin / "llvm-objdump"
        ),
        "llvm_objcopy": str(
            Path(args.llvm_objcopy).expanduser().resolve()
            if args.llvm_objcopy
            else llvm_bin / "llvm-objcopy"
        ),
        "qemu": str(Path(args.qemu).expanduser().resolve() if args.qemu else qemu_default),
        "model_root": str(model_root),
        "gfsim": str(gfsim),
    }


def tool_manifest(paths: dict[str, str]) -> dict[str, dict[str, Any]]:
    return {
        key: {
            "path": value,
            "exists": Path(value).exists(),
            "executable": executable(Path(value)),
        }
        for key, value in paths.items()
        if key != "model_root"
    } | {
        "model_root": {
            "path": paths["model_root"],
            "exists": Path(paths["model_root"]).exists(),
            "executable": False,
        }
    }


def command_text(command: str | list[str]) -> str:
    if isinstance(command, list):
        return shlex.join(str(c) for c in command)
    return command


def run_command(
    command: str | list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int,
    log_path: Path,
    dry_run: bool,
) -> dict[str, Any]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = command_text(command)
    log_path.write_text(f"$ {rendered}\n", encoding="utf-8")
    row = {
        "command": rendered,
        "cwd": str(cwd),
        "log": str(log_path),
        "timeout_seconds": timeout,
        "returncode": 0,
        "status": "not_run" if dry_run else "pass",
    }
    if dry_run:
        return row

    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            shell=isinstance(command, str),
            executable="/bin/bash" if isinstance(command, str) else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout if timeout > 0 else None,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        elif not isinstance(output, str):
            output = str(output)
        log_path.write_text(f"$ {rendered}\n\n{output}", encoding="utf-8", errors="replace")
        row["status"] = "timeout"
        row["returncode"] = 124
        return row

    log_path.write_text(
        f"$ {rendered}\n\n{proc.stdout or ''}",
        encoding="utf-8",
        errors="replace",
    )
    row["returncode"] = proc.returncode
    row["status"] = "pass" if proc.returncode == 0 else "fail"
    return row


def normalize_qemu_finisher_result(result: dict[str, Any], log_path: Path) -> dict[str, Any]:
    """Treat the Linx direct-boot test finisher as a successful QEMU exit."""
    returncode = int(result.get("returncode", 0))
    finisher_low8 = returncode & 0xFF
    if result.get("status") == "fail" and finisher_low8 == FINISHER_PASS_LOW8:
        result = dict(result)
        result["status"] = "pass"
        result["finisher"] = "pass"
        with log_path.open("a", encoding="utf-8", errors="replace") as log:
            log.write(f"\n[ai-flow] guest finisher pass exit={returncode}\n")
        return result
    if result.get("status") == "fail" and finisher_low8 == FINISHER_FAIL_LOW8:
        result = dict(result)
        result["finisher"] = "fail"
    elif result.get("status") == "fail" and finisher_low8 == FINISHER_RESET_LOW8:
        result = dict(result)
        result["finisher"] = "reset"
    return result


def parse_digests(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m.group(1): "0x" + m.group(2).upper() for m in DIGEST_RE.finditer(text)}


def summarize_gfsim_log(status: str, log_path: Path) -> tuple[str, dict[str, str]]:
    if status == "pass":
        return "gfsim passed", {}
    if not log_path.exists():
        return "gfsim failed; log missing", {}

    text = log_path.read_text(encoding="utf-8", errors="replace")
    artifacts: dict[str, str] = {}

    finisher = list(GFSIM_FINISHER_RE.finditer(text))
    if finisher:
        match = finisher[-1]
        value = "0x" + match.group("value").lower()
        finisher_status = match.group("status")
        artifacts["finisher_value"] = value
        artifacts["finisher_status"] = finisher_status
        return f"gfsim finisher {finisher_status} ({value})", artifacts

    assertion = GFSIM_ASSERT_RE.search(text)
    if assertion:
        reason = assertion.group("assertion").strip()
        artifacts["assertion"] = reason
        return f"gfsim {status}: {reason}", artifacts

    brob = list(GFSIM_BROB_RE.finditer(text))
    if brob:
        match = brob[-1]
        bpc = "0x" + match.group("bpc").lower()
        artifacts["last_brob_bpc"] = bpc
        artifacts["last_retired_blocks"] = match.group("blocks")
        artifacts["last_brob_head"] = match.group("head").strip()
        status_text = "timed out" if status == "timeout" else "failed"
        return f"gfsim {status_text}; last BROB head BPC {bpc}", artifacts

    if status == "timeout":
        return "gfsim timed out; no terminal model marker found", artifacts
    return "gfsim failed; no terminal model marker found", artifacts


def mark_failure(state: CaseState, stage_id: str, owner: str, evidence: str) -> None:
    if state.failure_stage is None:
        state.failure_stage = stage_id
        state.failure_owner = owner
        state.failure_evidence = evidence


def stage_row(
    state: CaseState,
    stage_id: str,
    status: str,
    *,
    owner: str,
    evidence: str = "",
    command: str | None = None,
    artifacts: dict[str, str] | None = None,
) -> dict[str, Any]:
    row = {
        "stage": stage_id,
        "status": status,
        "owner": owner,
        "evidence": evidence,
        "command": command,
        "artifacts": artifacts or {},
    }
    state.stages[stage_id] = row
    if status not in PASS_STATUSES:
        mark_failure(state, stage_id, owner, evidence)
    return row


def case_can_enter(state: CaseState, previous_stage: str) -> bool:
    row = state.stages.get(previous_stage)
    return row is not None and row["status"] in PASS_STATUSES


def source_contract(root: Path, states: list[CaseState], dry_run: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for state in states:
        case = state.case
        case_source_dir = state.case_dir / "source"
        artifacts: dict[str, str] = {}
        missing: list[str] = []
        source_rows: list[dict[str, str]] = []
        for source in case.source_paths:
            if not source.exists():
                missing.append(relpath(root, source))
                continue
            digest = sha256_file(source)
            source_rows.append({"path": relpath(root, source), "sha256": digest})
            case_source_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, case_source_dir / source.name)
        if case.manifest_path is not None:
            if not case.manifest_path.exists():
                missing.append(relpath(root, case.manifest_path))
            else:
                artifacts["manifest"] = relpath(root, case.manifest_path)
        source_manifest = state.case_dir / "source_manifest.json"
        write_json(
            source_manifest,
            {
                "case": case.id,
                "kind": case.kind,
                "suite": case.suite,
                "tier": case.tier,
                "sources": source_rows,
                "metadata": case.metadata,
                "dry_run": dry_run,
            },
        )
        artifacts["source_manifest"] = str(source_manifest)
        if missing:
            rows.append(
                stage_row(
                    state,
                    "source-contract",
                    "fail",
                    owner="benchmark",
                    evidence="missing source/manifest: " + ", ".join(missing),
                    artifacts=artifacts,
                )
            )
        else:
            rows.append(
                stage_row(
                    state,
                    "source-contract",
                    "pass",
                    owner="benchmark",
                    evidence=f"{len(source_rows)} source file(s) hashed",
                    artifacts=artifacts,
                )
            )
    return rows


def avs_command(
    root: Path,
    case: Case,
    paths: dict[str, str],
    out_dir: Path,
    *,
    timeout: int,
    compile_only: bool,
) -> list[str]:
    cmd = [
        sys.executable,
        str(root / "avs" / "qemu" / "run_tests.py"),
        "--suite",
        str(case.metadata["avs_suite"]),
        "--out-dir",
        str(out_dir),
        "--timeout",
        str(timeout),
        "--clang",
        paths["clang"],
        "--clangxx",
        paths["clangxx"],
        "--lld",
        paths["lld"],
        "--llvm-objdump",
        paths["llvm_objdump"],
    ]
    if compile_only:
        cmd.append("--compile-only")
    else:
        cmd += ["--qemu", paths["qemu"]]
        if case.metadata.get("avs_source_profile") == "compile-smoke":
            cmd.append("--smoke-source-overrides")
    return cmd


def pto_compile_command(root: Path, case: Case, paths: dict[str, str], asm_out: Path) -> list[str]:
    return [
        paths["clangxx"],
        "-target",
        "linx64-linx-none-elf",
        "-O2",
        "-S",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-stack-protector",
        "-fno-exceptions",
        "-fno-rtti",
        "-nostdlib",
        "-I",
        str(root / "workloads" / "pto_kernels" / "include"),
        str(case.source_paths[0]),
        "-o",
        str(asm_out),
    ]


def supernpu_make_command(
    case: Case,
    paths: dict[str, str],
    *,
    target: str | None = None,
    linker_script: Path | None = None,
    obj_root: Path | None = None,
) -> str:
    vars_part = " ".join(
        f"{shlex.quote(k)}={shlex.quote(str(v))}"
        for k, v in sorted(case.metadata["make_vars"].items())
    )
    obj_root_part = f" OBJ_ROOT={shlex.quote(str(obj_root))}" if obj_root is not None else ""
    compiler_dir = shlex.quote(str(Path(paths["clang"]).parent))
    linx_compile_flags = shlex.quote("-c -target linx64-linx-none-elf -fenable-matrix -O2")
    linker_flags = "-Wl,-e,_start"
    if linker_script is not None:
        linker_flags += f" -Wl,-T,{linker_script}"
    linx_link_flags = shlex.quote(f"-target linx64-linx-none-elf -nostdlib {linker_flags}")
    prefix = (
        f"make {vars_part} PLAT=linx COMPILER_DIR={compiler_dir} "
        f"CC_O={linx_compile_flags} CC_LINK={linx_link_flags}{obj_root_part}"
    )
    if target:
        return f"{prefix} {shlex.quote(target)}"
    bench_root = next((p for p in [case.workdir, *case.workdir.parents] if p.name == "SuperNPUBench"), None)
    output_root = obj_root if obj_root is not None else (bench_root / "output" if bench_root else None)
    mkdir_output = f"mkdir -p {shlex.quote(str(output_root))}" if output_root else "true"
    clean = f"make{obj_root_part} clean" if obj_root_part else "make clean"
    return f"{mkdir_output} && {clean} && {prefix}"


def classify_supernpu_compile_failure(log_path: Path) -> tuple[str, str]:
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    source_markers = [
        "-mlxbc",
        "-enable-all-vector-as-tilereg",
        "bits/alltypes.h",
        "unknown type name '__half'",
        "use of undeclared identifier '__fp32'",
        "use of undeclared identifier '__tf32'",
        "use of undeclared identifier '__hf32'",
        "include/c++/v1/iostream",
        "workloads/SuperNPUBench/include/jcore/type.hpp",
    ]
    if any(marker in text for marker in source_markers):
        return "benchmark", "SuperNPUBench source/toolchain manifest mismatch"
    return "compiler", "SuperNPUBench compile failed"


def classify_avs_compile_failure(log_path: Path) -> tuple[str, str]:
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    source_markers = [
        "__builtin_linx_lc",
        "<<<",
        ">>>",
        "PTO kernel",
        "block_vector_kernels.hpp",
        "block_vector_compat.hpp",
    ]
    if any(marker in text for marker in source_markers):
        return "benchmark", "AVS PTO source/API contract failed under Linx clang"
    return "compiler", "AVS compile failed"


def run_obj_tool(
    tool: str,
    args: list[str],
    *,
    cwd: Path,
    out_path: Path,
    timeout: int,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8")
        return {"status": "not_run", "command": shlex.join([tool, *args]), "output": str(out_path)}
    proc = subprocess.run(
        [tool, *args],
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(proc.stdout or "", encoding="utf-8", errors="replace")
    return {
        "status": "pass" if proc.returncode == 0 else "fail",
        "returncode": proc.returncode,
        "command": shlex.join([tool, *args]),
        "output": str(out_path),
    }


def static_check_text(text: str, *, require_entry: bool) -> tuple[bool, list[str]]:
    findings: list[str] = []
    if FORBIDDEN_ASM_RE.search(text):
        findings.append("forbidden retired pre-v0.56 token found")
    if require_entry and not re.search(r"(\b_start\b|\bmain\b)", text):
        findings.append("missing _start/main symbol in objdump evidence")
    return not findings, findings


def compiler_contract(
    root: Path,
    states: list[CaseState],
    paths: dict[str, str],
    dry_run: bool,
    timeout: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    env = os.environ.copy()
    env.setdefault("LINXISA_ROOT", str(root))
    for state in states:
        case = state.case
        if not case_can_enter(state, "source-contract"):
            rows.append(
                stage_row(
                    state,
                    "compiler-contract",
                    "skipped",
                    owner="compiler",
                    evidence="source contract did not pass",
                )
            )
            continue
        case_artifacts = state.case_dir / "compiler"
        log_path = case_artifacts / "compile.log"
        artifacts: dict[str, str] = {}
        if case.kind == "avs_pto":
            out_dir = case_artifacts / "avs"
            cmd = avs_command(root, case, paths, out_dir, timeout=timeout, compile_only=True)
            result = run_command(
                cmd,
                cwd=root,
                env=env,
                timeout=timeout,
                log_path=log_path,
                dry_run=dry_run,
            )
            obj = out_dir / "linx-qemu-tests.o"
            artifacts.update({"log": str(log_path), "object": str(obj)})
            if result["status"] == "pass" and obj.exists():
                state.artifacts["object"] = str(obj)
            owner = "compiler"
            evidence = (
                "AVS direct-boot suite compiled"
                if result["status"] == "pass"
                else "AVS compile failed"
            )
            if result["status"] not in PASS_STATUSES:
                owner, evidence = classify_avs_compile_failure(log_path)
            rows.append(
                stage_row(
                    state,
                    "compiler-contract",
                    result["status"],
                    owner=owner,
                    evidence=evidence,
                    command=result["command"],
                    artifacts=artifacts,
                )
            )
            continue

        if case.kind == "pto_kernel":
            asm_out = case_artifacts / f"{case.id}.s"
            cmd = pto_compile_command(root, case, paths, asm_out)
            result = run_command(
                cmd,
                cwd=root,
                env=env,
                timeout=timeout,
                log_path=log_path,
                dry_run=dry_run,
            )
            artifacts.update({"log": str(log_path), "asm": str(asm_out)})
            status = result["status"]
            evidence = "PTO kernel compiled to Linx assembly"
            if status == "pass" and asm_out.exists():
                text = asm_out.read_text(encoding="utf-8", errors="replace")
                ok, findings = static_check_text(text, require_entry=False)
                if not ok:
                    status = "fail"
                    evidence = "; ".join(findings)
                state.artifacts["asm"] = str(asm_out)
            elif status == "not_run":
                evidence = "dry-run compile command recorded"
            else:
                evidence = "PTO kernel compile failed"
            rows.append(
                stage_row(
                    state,
                    "compiler-contract",
                    status,
                    owner="compiler",
                    evidence=evidence,
                    command=result["command"],
                    artifacts=artifacts,
                )
            )
            continue

        if case.kind == "supernpu":
            linker_script = case_artifacts / "linx-supernpu-directboot.ld"
            linker_script.parent.mkdir(parents=True, exist_ok=True)
            linker_script.write_text(LINX_DIRECT_BOOT_LINK_SCRIPT, encoding="utf-8")
            artifacts["linker_script"] = str(linker_script)
            supernpu_output = case_artifacts / "supernpu-output"
            elf_dir = supernpu_output / case.suite / "elf"
            artifacts["obj_root"] = str(supernpu_output)
            before_elves = snapshot_elf_mtimes(elf_dir)
            cmd = supernpu_make_command(
                case,
                paths,
                linker_script=linker_script,
                obj_root=supernpu_output,
            )
            result = run_command(
                cmd,
                cwd=case.workdir,
                env=env,
                timeout=timeout,
                log_path=log_path,
                dry_run=dry_run,
            )
            metadata_elf = Path(case.metadata["elf"])
            elf = elf_dir / metadata_elf.name
            artifacts["log"] = str(log_path)
            artifacts["elf_source"] = str(elf)
            status = result["status"]
            evidence = "SuperNPUBench case compiled to Linx ELF"
            owner = "compiler"
            if status == "pass":
                if not dry_run:
                    actual_elf = find_supernpu_elf_after_compile(
                        case,
                        root,
                        before_elves,
                        elf_dir=elf_dir,
                    )
                    if actual_elf is not None:
                        elf = actual_elf
                        artifacts["elf_source"] = str(elf)
                if not dry_run and not elf.exists():
                    status = "fail"
                    evidence = f"expected ELF was not produced: {elf}"
                else:
                    copied = case_artifacts / f"{case.id}.elf"
                    copied.parent.mkdir(parents=True, exist_ok=True)
                    if not dry_run and elf.exists():
                        shutil.copy2(elf, copied)
                    state.artifacts["elf"] = str(copied)
                    artifacts["elf"] = str(copied)
                    objdump = Path(paths["llvm_objdump"])
                    if dry_run or executable(objdump):
                        dump = run_obj_tool(
                            paths["llvm_objdump"],
                            ["-d", str(copied)],
                            cwd=root,
                            out_path=case_artifacts / "objdump.disasm.txt",
                            timeout=120,
                            dry_run=dry_run,
                        )
                        sym = run_obj_tool(
                            paths["llvm_objdump"],
                            ["-t", str(copied)],
                            cwd=root,
                            out_path=case_artifacts / "objdump.symbols.txt",
                            timeout=120,
                            dry_run=dry_run,
                        )
                        sec = run_obj_tool(
                            paths["llvm_objdump"],
                            ["-h", str(copied)],
                            cwd=root,
                            out_path=case_artifacts / "objdump.sections.txt",
                            timeout=120,
                            dry_run=dry_run,
                        )
                        rel = run_obj_tool(
                            paths["llvm_objdump"],
                            ["-r", str(copied)],
                            cwd=root,
                            out_path=case_artifacts / "objdump.relocs.txt",
                            timeout=120,
                            dry_run=dry_run,
                        )
                        artifacts.update(
                            {
                                "disasm": dump["output"],
                                "symbols": sym["output"],
                                "sections": sec["output"],
                                "relocations": rel["output"],
                            }
                        )
                        if not dry_run:
                            text = "\n".join(
                                Path(p).read_text(encoding="utf-8", errors="replace")
                                for p in [dump["output"], sym["output"], sec["output"], rel["output"]]
                                if Path(p).exists()
                            )
                            ok, findings = static_check_text(text, require_entry=True)
                            if not ok:
                                status = "fail"
                                evidence = "; ".join(findings)
                    objcopy = Path(paths["llvm_objcopy"])
                    if dry_run or executable(objcopy):
                        raw = case_artifacts / f"{case.id}.bin"
                        objcopy_row = run_obj_tool(
                            paths["llvm_objcopy"],
                            ["-O", "binary", str(copied), str(raw)],
                            cwd=root,
                            out_path=case_artifacts / "objcopy.log",
                            timeout=120,
                            dry_run=dry_run,
                        )
                        artifacts["raw_bin"] = str(raw)
                        artifacts["objcopy_log"] = objcopy_row["output"]
            elif status == "not_run":
                copied = case_artifacts / f"{case.id}.elf"
                state.artifacts["elf"] = str(copied)
                artifacts["elf"] = str(copied)
                evidence = "dry-run compile command recorded"
                owner = "compiler"
            else:
                owner, evidence = classify_supernpu_compile_failure(log_path)
            rows.append(
                stage_row(
                    state,
                    "compiler-contract",
                    status,
                    owner=owner,
                    evidence=evidence,
                    command=result["command"],
                    artifacts=artifacts,
                )
            )
            continue

        rows.append(
            stage_row(
                state,
                "compiler-contract",
                "fail",
                owner="compiler",
                evidence=f"unsupported case kind: {case.kind}",
            )
        )
    return rows


def qemu_execution(
    root: Path,
    states: list[CaseState],
    paths: dict[str, str],
    dry_run: bool,
    timeout: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    env = os.environ.copy()
    env.setdefault("LINXISA_ROOT", str(root))
    for state in states:
        case = state.case
        if not case_can_enter(state, "compiler-contract"):
            rows.append(
                stage_row(
                    state,
                    "qemu-execution",
                    "skipped",
                    owner="emulator",
                    evidence="compiler contract did not pass",
                )
            )
            continue
        if not case.produces_elf:
            rows.append(
                stage_row(
                    state,
                    "qemu-execution",
                    "not_applicable",
                    owner="emulator",
                    evidence="case has no standalone ELF harness yet",
                )
            )
            continue
        artifacts: dict[str, str] = {}
        case_artifacts = state.case_dir / "qemu"
        log_path = case_artifacts / "qemu.log"
        if case.kind == "avs_pto":
            out_dir = state.case_dir / "compiler" / "avs"
            cmd = avs_command(root, case, paths, out_dir, timeout=timeout, compile_only=False)
            result = run_command(
                cmd,
                cwd=root,
                env=env,
                timeout=timeout + 120,
                log_path=log_path,
                dry_run=dry_run,
            )
            elf = out_dir / "linx-qemu-tests.elf"
            artifacts.update({"log": str(log_path), "elf": str(elf)})
            if result["status"] == "pass" or dry_run:
                state.artifacts["elf"] = str(elf)
                if result["status"] == "pass":
                    state.qemu_digests = parse_digests(log_path)
            rows.append(
                stage_row(
                    state,
                    "qemu-execution",
                    result["status"],
                    owner="emulator",
                    evidence="QEMU direct-boot AVS suite passed" if result["status"] == "pass" else "QEMU direct-boot AVS suite failed",
                    command=result["command"],
                    artifacts=artifacts,
                )
            )
            continue
        if case.kind == "supernpu":
            elf_text = state.artifacts.get("elf")
            if elf_text:
                elf = Path(elf_text)
            else:
                metadata_elf = Path(case.metadata["elf"])
                elf = metadata_elf if metadata_elf.is_absolute() else root / metadata_elf
            if not elf.exists() and not dry_run:
                rows.append(
                    stage_row(
                        state,
                        "qemu-execution",
                        "fail",
                        owner="emulator",
                        evidence="missing compiler-produced ELF for QEMU",
                    )
                )
                continue
            cmd = [
                paths["qemu"],
                "-machine",
                "virt",
                "-bios",
                "none",
                "-kernel",
                str(elf),
                "-nographic",
                "-monitor",
                "none",
            ]
            result = run_command(
                cmd,
                cwd=root,
                env=env,
                timeout=timeout,
                log_path=log_path,
                dry_run=dry_run,
            )
            result = normalize_qemu_finisher_result(result, log_path)
            artifacts.update({"log": str(log_path), "elf": str(elf)})
            if result["status"] == "pass":
                state.qemu_digests = parse_digests(log_path)
            rows.append(
                stage_row(
                    state,
                    "qemu-execution",
                    result["status"],
                    owner="emulator",
                    evidence="SuperNPUBench ELF passed QEMU" if result["status"] == "pass" else "SuperNPUBench QEMU execution failed",
                    command=result["command"],
                    artifacts=artifacts,
                )
            )
            continue
        rows.append(
            stage_row(
                state,
                "qemu-execution",
                "not_applicable",
                owner="emulator",
                evidence=f"QEMU stage not defined for kind {case.kind}",
            )
        )
    return rows


def find_smoke_elf(states: list[CaseState], override: str | None) -> Path | None:
    if override:
        return Path(override).expanduser().resolve()
    return None


def build_model_smoke_elf(
    root: Path,
    paths: dict[str, str],
    stage_dir: Path,
    env: dict[str, str],
    dry_run: bool,
    timeout: int,
) -> tuple[Path, list[dict[str, Any]]]:
    source = stage_dir / "linx-model-smoke.cpp"
    linker = stage_dir / "linx-model-smoke.ld"
    elf = stage_dir / "linx-model-smoke.elf"
    source.write_text(LINX_MODEL_SMOKE_SOURCE, encoding="utf-8")
    linker.write_text(LINX_DIRECT_BOOT_LINK_SCRIPT, encoding="utf-8")
    cmd = [
        paths["clangxx"],
        "-target",
        "linx64-linx-none-elf",
        "-O2",
        "-ffreestanding",
        "-fno-builtin",
        "-fno-stack-protector",
        "-fno-exceptions",
        "-fno-rtti",
        "-nostdlib",
        str(source),
        "-Wl,-e,_start",
        f"-Wl,-T,{linker}",
        "-o",
        str(elf),
    ]
    row = run_command(
        cmd,
        cwd=root,
        env=env,
        timeout=timeout,
        log_path=stage_dir / "linx-model-smoke-compile.log",
        dry_run=dry_run,
    )
    return elf, [row]


def model_build_smoke(
    root: Path,
    states: list[CaseState],
    paths: dict[str, str],
    dry_run: bool,
    build_timeout: int,
    smoke_timeout: int,
    skip_build: bool,
    smoke_elf_override: str | None,
) -> dict[str, Any]:
    model_root = Path(paths["model_root"])
    gfsim = Path(paths["gfsim"])
    stage_dir = states[0].case_dir.parent / "_model" if states else root / "workloads" / "generated" / "_model"
    stage_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    rows: list[dict[str, Any]] = []
    if not dry_run and not skip_build:
        configure = run_command(
            [
                "cmake",
                "-S",
                str(model_root),
                "-B",
                str(model_root / "build"),
                "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            ],
            cwd=root,
            env=env,
            timeout=build_timeout,
            log_path=stage_dir / "cmake-configure.log",
            dry_run=False,
        )
        rows.append(configure)
        if configure["status"] == "pass":
            build = run_command(
                ["cmake", "--build", str(model_root / "build"), "--target", "gfsim"],
                cwd=root,
                env=env,
                timeout=build_timeout,
                log_path=stage_dir / "cmake-build-gfsim.log",
                dry_run=False,
            )
            rows.append(build)
    elif dry_run:
        rows.append(
            {
                "status": "not_run",
                "command": f"cmake -S {model_root} -B {model_root / 'build'} -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && cmake --build {model_root / 'build'} --target gfsim",
                "log": str(stage_dir / "cmake-build-gfsim.log"),
            }
        )

    smoke_elf = find_smoke_elf(states, smoke_elf_override)
    if smoke_elf is None:
        smoke_elf, smoke_compile_rows = build_model_smoke_elf(
            root,
            paths,
            stage_dir,
            env,
            dry_run,
            build_timeout,
        )
        rows.extend(smoke_compile_rows)
    else:
        smoke_compile_rows = []

    gfsim_exists = dry_run or executable(gfsim)
    smoke_row: dict[str, Any] | None = None
    if gfsim_exists and smoke_elf is not None:
        smoke_cmd = [str(gfsim), "-f", str(smoke_elf)]
        smoke_row = run_command(
            smoke_cmd,
            cwd=model_root,
            env=env,
            timeout=smoke_timeout,
            log_path=stage_dir / "gfsim-smoke.log",
            dry_run=dry_run,
        )
        rows.append(smoke_row)

    failed_build = next((row for row in rows if row.get("status") not in PASS_STATUSES), None)
    owner = "model"
    if failed_build is not None:
        status = failed_build["status"]
        owner = "compiler" if failed_build in smoke_compile_rows else "model"
        if failed_build in smoke_compile_rows:
            evidence = "model smoke ELF compile timed out" if status == "timeout" else "model smoke ELF compile failed"
        else:
            evidence = "LinxCoreModel build/smoke timed out" if status == "timeout" else "LinxCoreModel build/smoke failed"
    elif not gfsim_exists:
        status = "fail"
        evidence = f"gfsim not found or not executable: {gfsim}"
    elif smoke_elf is None:
        status = "skipped"
        evidence = "no QEMU-passing smoke ELF available yet"
    elif smoke_row and smoke_row["status"] == "not_run":
        status = "not_run"
        evidence = "dry-run model build/smoke recorded"
    else:
        status = "pass"
        evidence = "gfsim available and smoke command passed"

    row = {
        "stage": "model-build-smoke",
        "status": status,
        "owner": owner,
        "evidence": evidence,
        "gfsim": str(gfsim),
        "smoke_elf": str(smoke_elf) if smoke_elf is not None else None,
        "commands": rows,
    }
    artifacts = {
        "gfsim": str(gfsim),
        "configure_log": str(stage_dir / "cmake-configure.log"),
        "build_log": str(stage_dir / "cmake-build-gfsim.log"),
        "smoke_log": str(stage_dir / "gfsim-smoke.log"),
    }
    if smoke_elf is not None:
        artifacts["smoke_elf"] = str(smoke_elf)
    if smoke_elf_override is None:
        artifacts.update(
            {
                "smoke_source": str(stage_dir / "linx-model-smoke.cpp"),
                "smoke_linker_script": str(stage_dir / "linx-model-smoke.ld"),
                "smoke_compile_log": str(stage_dir / "linx-model-smoke-compile.log"),
            }
        )
    for state in states:
        state.stages["model-build-smoke"] = {
            "stage": "model-build-smoke",
            "status": status,
            "owner": owner,
            "evidence": evidence,
            "command": row["commands"][-1]["command"] if row["commands"] else None,
            "commands": rows,
            "artifacts": artifacts,
        }
        if status not in PASS_STATUSES:
            mark_failure(state, "model-build-smoke", owner, evidence)
    return row


def linxcoremodel_execution(
    states: list[CaseState],
    paths: dict[str, str],
    dry_run: bool,
    timeout: int,
    model_stage_ok: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    model_root = Path(paths["model_root"])
    gfsim = Path(paths["gfsim"])
    env = os.environ.copy()
    for state in states:
        case = state.case
        qemu_row = state.stages.get("qemu-execution")
        if not model_stage_ok:
            rows.append(
                stage_row(
                    state,
                    "linxcoremodel-execution",
                    "skipped",
                    owner="model",
                    evidence="model build/smoke did not pass",
                )
            )
            continue
        if not case.model_eligible or not case.produces_elf:
            rows.append(
                stage_row(
                    state,
                    "linxcoremodel-execution",
                    "not_applicable",
                    owner="model",
                    evidence="case is not model-eligible yet",
                )
            )
            continue
        if qemu_row is None or qemu_row["status"] != "pass":
            rows.append(
                stage_row(
                    state,
                    "linxcoremodel-execution",
                    "skipped",
                    owner="model",
                    evidence="QEMU did not pass for this case",
                )
            )
            continue
        elf = Path(state.artifacts.get("elf", ""))
        if not dry_run and not elf.exists():
            rows.append(
                stage_row(
                    state,
                    "linxcoremodel-execution",
                    "fail",
                    owner="model",
                    evidence=f"missing QEMU-passing ELF: {elf}",
                )
            )
            continue
        log_path = state.case_dir / "model" / "gfsim.log"
        cmd = [str(gfsim), "-f", str(elf)]
        result = run_command(
            cmd,
            cwd=model_root,
            env=env,
            timeout=timeout,
            log_path=log_path,
            dry_run=dry_run,
        )
        if result["status"] == "pass":
            state.model_digests = parse_digests(log_path)
        evidence, diagnostics = summarize_gfsim_log(result["status"], log_path)
        artifacts = {"log": str(log_path), "elf": str(elf)}
        artifacts.update(diagnostics)
        rows.append(
            stage_row(
                state,
                "linxcoremodel-execution",
                result["status"],
                owner="model",
                evidence=evidence,
                command=result["command"],
                artifacts=artifacts,
            )
        )
    return rows


def differential_triage(states: list[CaseState]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for state in states:
        case = state.case
        qemu = state.qemu_digests
        model = state.model_digests
        status = "pass"
        evidence = "no digest comparison required"
        if qemu and model:
            missing = sorted(set(qemu) ^ set(model))
            mismatched = sorted(k for k in set(qemu) & set(model) if qemu[k] != model[k])
            if missing or mismatched:
                status = "fail"
                evidence = (
                    f"digest mismatch; missing={missing or []}; mismatched={mismatched or []}"
                )
                mark_failure(state, "differential-triage", "model", evidence)
            else:
                evidence = f"{len(qemu)} digest(s) matched between QEMU and model"
        elif qemu and not model:
            model_row = state.stages.get("linxcoremodel-execution", {})
            if model_row.get("status") == "pass":
                status = "fail"
                evidence = "QEMU emitted digests but model emitted none"
                mark_failure(state, "differential-triage", "model", evidence)
            else:
                status = "skipped"
                evidence = "model did not pass, digest comparison skipped"
        elif state.failure_stage:
            status = "skipped"
            evidence = f"first failure already assigned to {state.failure_owner}"
        rows.append(
            stage_row(
                state,
                "differential-triage",
                status,
                owner=state.failure_owner or "integration",
                evidence=evidence,
                artifacts={
                    "qemu_digest_count": str(len(qemu)),
                    "model_digest_count": str(len(model)),
                },
            )
        )
    return rows


def write_fix_packets(out_dir: Path, states: list[CaseState]) -> list[dict[str, Any]]:
    packet_dir = out_dir / "fix-packets"
    rows: list[dict[str, Any]] = []
    for state in states:
        if not state.failure_stage:
            rows.append(
                stage_row(
                    state,
                    "fix-packets",
                    "not_applicable",
                    owner="integration",
                    evidence="case is green or only skipped for non-applicable stages",
                )
            )
            continue
        case = state.case
        failed_row = state.stages.get(state.failure_stage, {})
        packet = {
            "schema_version": 1,
            "generated_at_utc": utc_now(),
            "case": {
                "id": case.id,
                "kind": case.kind,
                "suite": case.suite,
                "tier": case.tier,
                "sources": [str(path) for path in case.source_paths],
                "manifest": str(case.manifest_path) if case.manifest_path else None,
                "workdir": str(case.workdir),
                "model_eligible": case.model_eligible,
                "produces_elf": case.produces_elf,
                "expected": case.expected,
                "metadata": case.metadata,
            },
            "failure": {
                "stage": state.failure_stage,
                "owner": state.failure_owner,
                "evidence": state.failure_evidence,
                "row": failed_row,
            },
            "repro": {
                "command": failed_row.get("command"),
                "cwd": str(case.workdir),
                "expected_next_boundary": next_boundary(state.failure_stage),
            },
            "artifacts": state.artifacts,
            "stage_rows": state.stages,
        }
        packet_path = packet_dir / f"{case.id}.json"
        write_json(packet_path, packet)
        rows.append(
            stage_row(
                state,
                "fix-packets",
                "pass",
                owner="integration",
                evidence=f"fix packet emitted for {state.failure_owner}",
                artifacts={"fix_packet": str(packet_path)},
            )
        )
    return rows


def next_boundary(stage_id: str | None) -> str:
    order = [
        "source-contract",
        "compiler-contract",
        "qemu-execution",
        "model-build-smoke",
        "linxcoremodel-execution",
        "differential-triage",
    ]
    if stage_id not in order:
        return "source-contract"
    idx = order.index(stage_id)
    return order[min(idx + 1, len(order) - 1)]


def write_skill_doc_evolution(out_dir: Path, states: list[CaseState], evolve_note: str | None = None) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for state in states:
        if state.failure_owner:
            counts[state.failure_owner] = counts.get(state.failure_owner, 0) + 1
    if evolve_note:
        line = f"skill-evolve: update {evolve_note}"
    else:
        line = "skill-evolve: no-update (runner emitted reusable evidence; update skills only after a material repeated finding)"
    payload = {
        "stage": "skill-doc-evolution",
        "status": "pass",
        "owner": "docs-skills",
        "generated_at_utc": utc_now(),
        "skill_evolve": line,
        "failure_owner_counts": counts,
        "documentation": [
            "docs/bringup/ai_workload_bringup_flow.json",
            "tools/bringup/run_ai_workload_flow.py",
        ],
    }
    write_json(out_dir / "skill_evolution.json", payload)
    (out_dir / "skill_evolution.md").write_text(
        "# Skill And Documentation Evolution\n\n"
        f"- {line}\n"
        f"- Failure owner counts: `{json.dumps(counts, sort_keys=True)}`\n",
        encoding="utf-8",
    )
    return payload


def stage_failed(rows: list[dict[str, Any]] | dict[str, Any]) -> bool:
    if isinstance(rows, dict):
        return rows.get("status") not in PASS_STATUSES
    return any(row.get("status") not in PASS_STATUSES for row in rows)


def case_summary(state: CaseState) -> dict[str, Any]:
    final_status = "fail" if state.failure_stage else "pass"
    if not state.failure_stage:
        model_row = state.stages.get("linxcoremodel-execution")
        if model_row and model_row["status"] in {"skipped", "not_applicable", "not_run"}:
            final_status = model_row["status"]
    return {
        "id": state.case.id,
        "kind": state.case.kind,
        "suite": state.case.suite,
        "tier": state.case.tier,
        "final_status": final_status,
        "failure_stage": state.failure_stage,
        "failure_owner": state.failure_owner,
        "failure_evidence": state.failure_evidence,
        "artifacts": state.artifacts,
        "stages": state.stages,
    }


def write_manifest(
    root: Path,
    out_dir: Path,
    *,
    flow: dict[str, Any],
    profile: str,
    tiers: set[int],
    dry_run: bool,
    paths: dict[str, str],
    cases: list[Case],
) -> None:
    submodules = [
        "compiler/llvm",
        "emulator/qemu",
        "model/LinxCoreModel",
        "tools/model",
        "workloads/pto_kernels",
        "workloads/SuperNPUBench",
        "skills/linx-skills",
    ]
    payload = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "flow_id": flow.get("flow_id"),
        "profile": profile,
        "tiers": sorted(tiers),
        "dry_run": dry_run,
        "repo_root": str(root),
        "tools": tool_manifest(paths),
        "submodules": {rel: submodule_sha(root, rel) for rel in submodules},
        "cases": [
            {
                "id": case.id,
                "kind": case.kind,
                "suite": case.suite,
                "tier": case.tier,
                "sources": [relpath(root, p) for p in case.source_paths],
                "manifest": relpath(root, case.manifest_path) if case.manifest_path else None,
                "model_eligible": case.model_eligible,
                "produces_elf": case.produces_elf,
                "expected": case.expected,
                "metadata": case.metadata,
            }
            for case in cases
        ],
    }
    write_json(out_dir / "manifest.json", payload)


def write_report(
    out_dir: Path,
    *,
    flow: dict[str, Any],
    profile: str,
    tiers: set[int],
    dry_run: bool,
    stages: list[dict[str, Any]],
    states: list[CaseState],
    skill_evolution: dict[str, Any] | None,
) -> None:
    payload = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "flow_id": flow.get("flow_id"),
        "profile": profile,
        "tiers": sorted(tiers),
        "dry_run": dry_run,
        "ok": all(not state.failure_stage for state in states),
        "stages": stages,
        "cases": [case_summary(state) for state in states],
        "skill_evolution": skill_evolution,
    }
    write_json(out_dir / "report.json", payload)


def write_summary(out_dir: Path, states: list[CaseState], skill_evolution: dict[str, Any] | None) -> None:
    total = len(states)
    failures = [s for s in states if s.failure_stage]
    final_green = [
        s
        for s in states
        if not s.failure_stage
        and s.stages.get("linxcoremodel-execution", {}).get("status") == "pass"
    ]
    lines = [
        "# AI Workload Bring-Up Summary",
        "",
        f"- Generated (UTC): `{utc_now()}`",
        f"- Cases selected: `{total}`",
        f"- Final model green: `{len(final_green)}`",
        f"- Failed cases: `{len(failures)}`",
        "",
        "| Case | Kind | Tier | Final | First Owner | Evidence |",
        "|---|---:|---:|---|---|---|",
    ]
    for state in states:
        summary = case_summary(state)
        evidence = (summary.get("failure_evidence") or "").replace("|", "\\|")
        lines.append(
            f"| `{state.case.id}` | `{state.case.kind}` | `{state.case.tier}` | "
            f"`{summary['final_status']}` | `{summary.get('failure_owner') or '-'}` | {evidence or '-'} |"
        )
    if skill_evolution:
        lines += ["", "## Skill Evolution", "", f"- {skill_evolution['skill_evolve']}"]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_stage_list(stages: list[dict[str, Any]], cases: list[Case]) -> None:
    for idx, stage in enumerate(stages, start=1):
        hard = "hard-break" if stage.get("hard_break", True) else "non-blocking"
        print(f"{idx}. {stage['id']} [{stage.get('owner', 'unknown')}/{hard}]")
        if stage.get("why"):
            print(f"   {stage['why']}")
    print()
    for case in cases:
        print(f"{case.id} [{case.kind}/tier-{case.tier}] {case.suite}")


def main(argv: list[str]) -> int:
    root = repo_root()
    ap = argparse.ArgumentParser(
        description="Run the AI workload hard-break flow through Linx LLVM, QEMU, and LinxCoreModel."
    )
    ap.add_argument("--flow", default=str(default_flow_path(root)))
    ap.add_argument("--profile", default="smoke")
    ap.add_argument("--tier", type=int, action="append", default=[], help="Override profile tiers; may repeat")
    ap.add_argument("--case", action="append", default=[], help="Select cases whose id/suite/kind contains this text; may repeat")
    ap.add_argument("--kind", action="append", choices=["avs_pto", "pto_kernel", "supernpu"], default=[])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stage", action="append", default=[], help="Run one stage id; may repeat")
    ap.add_argument("--start-at", default=None)
    ap.add_argument("--stop-after", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--continue-on-fail", action="store_true")
    ap.add_argument("--run-id", default=default_run_id())
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--clang", default="")
    ap.add_argument("--clangxx", default="")
    ap.add_argument("--lld", default="")
    ap.add_argument("--llvm-objdump", default="")
    ap.add_argument("--llvm-objcopy", default="")
    ap.add_argument("--qemu", default="")
    ap.add_argument("--model-root", default="")
    ap.add_argument("--gfsim", default="")
    ap.add_argument("--model-smoke-elf", default="")
    ap.add_argument("--skip-model-build", action="store_true")
    ap.add_argument("--skill-evolve-note", default="", help="Emit `skill-evolve: update <note>` in the run closeout")
    ap.add_argument("--compile-timeout", type=int, default=900)
    ap.add_argument("--qemu-timeout", type=int, default=240)
    ap.add_argument("--model-timeout", type=int, default=600)
    ap.add_argument("--model-build-timeout", type=int, default=3600)
    args = ap.parse_args(argv)

    flow_path = Path(args.flow).resolve()
    flow = load_flow(flow_path)
    stages = selected_stages(flow, args.profile, args.stage, args.start_at, args.stop_after)
    tiers = profile_tiers(flow, args.profile, args.tier)
    all_cases = discover_cases(root)
    cases = filter_cases(all_cases, tiers, args.kind, args.case, args.limit)
    if not cases:
        raise SystemExit("error: no cases selected")

    if args.list:
        print_stage_list(stages, cases)
        return 0

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else root / "workloads" / "generated" / args.run_id / "ai-bringup"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = tool_paths(root, args)
    states = [CaseState(case=case, case_dir=out_dir / "cases" / case.id) for case in cases]
    write_manifest(
        root,
        out_dir,
        flow=flow,
        profile=args.profile,
        tiers=tiers,
        dry_run=args.dry_run,
        paths=paths,
        cases=cases,
    )

    stage_reports: list[dict[str, Any]] = []
    failed = False
    model_stage_status = True
    skill_evolution: dict[str, Any] | None = None

    for stage in stages:
        stage_id = stage["id"]
        print(f"== {stage_id} ({stage.get('owner', 'unknown')})")
        if stage_id == "source-contract":
            rows: list[dict[str, Any]] | dict[str, Any] = source_contract(root, states, args.dry_run)
        elif stage_id == "compiler-contract":
            rows = compiler_contract(root, states, paths, args.dry_run, args.compile_timeout)
        elif stage_id == "qemu-execution":
            rows = qemu_execution(root, states, paths, args.dry_run, args.qemu_timeout)
        elif stage_id == "model-build-smoke":
            rows = model_build_smoke(
                root,
                states,
                paths,
                args.dry_run,
                args.model_build_timeout,
                args.model_timeout,
                args.skip_model_build,
                args.model_smoke_elf or None,
            )
            model_stage_status = rows.get("status") in PASS_STATUSES
        elif stage_id == "linxcoremodel-execution":
            rows = linxcoremodel_execution(
                states,
                paths,
                args.dry_run,
                args.model_timeout,
                model_stage_status,
            )
        elif stage_id == "differential-triage":
            rows = differential_triage(states)
        elif stage_id == "fix-packets":
            rows = write_fix_packets(out_dir, states)
        elif stage_id == "skill-doc-evolution":
            skill_evolution = write_skill_doc_evolution(out_dir, states, args.skill_evolve_note or None)
            rows = skill_evolution
        else:
            raise SystemExit(f"error: unsupported stage id in flow: {stage_id}")

        stage_reports.append(
            {
                "id": stage_id,
                "owner": stage.get("owner"),
                "hard_break": bool(stage.get("hard_break", True)),
                "result": rows,
            }
        )
        write_report(
            out_dir,
            flow=flow,
            profile=args.profile,
            tiers=tiers,
            dry_run=args.dry_run,
            stages=stage_reports,
            states=states,
            skill_evolution=skill_evolution,
        )
        write_summary(out_dir, states, skill_evolution)
        if stage_failed(rows):
            failed = True
            if stage.get("hard_break", True) and not args.continue_on_fail:
                print(f"hard-break: stopping at stage {stage_id}")
                break

    emitted_stage_ids = {stage["id"] for stage in stage_reports}
    if any(state.failure_stage for state in states) and "fix-packets" not in emitted_stage_ids:
        rows = write_fix_packets(out_dir, states)
        stage_reports.append(
            {
                "id": "fix-packets",
                "owner": "integration",
                "hard_break": False,
                "result": rows,
            }
        )

    if skill_evolution is None:
        skill_evolution = write_skill_doc_evolution(out_dir, states)
        stage_reports.append(
            {
                "id": "skill-doc-evolution",
                "owner": "docs-skills",
                "hard_break": False,
                "result": skill_evolution,
            }
        )

    write_report(
        out_dir,
        flow=flow,
        profile=args.profile,
        tiers=tiers,
        dry_run=args.dry_run,
        stages=stage_reports,
        states=states,
        skill_evolution=skill_evolution,
    )
    write_summary(out_dir, states, skill_evolution)

    print(f"manifest: {out_dir / 'manifest.json'}")
    print(f"report: {out_dir / 'report.json'}")
    print(f"summary: {out_dir / 'summary.md'}")
    if failed:
        return 1
    print("ok: AI workload flow complete" if not args.dry_run else "ok: AI workload dry-run complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
