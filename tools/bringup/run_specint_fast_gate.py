#!/usr/bin/env python3
"""Run the fast SPECint QEMU gate over test/train input sets.

The private SPEC corpus and low-level SPEC runner live under ignored paths.
This tracked wrapper keeps the public gate policy stable: small test/train
suites first, expensive promotion work only in the nightly profile.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from qemu_build_paths import default_qemu_binary


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_DIR = REPO_ROOT / "workloads" / "spec2017" / "cpu2017v118_x64_gcc12_avx2"
DEFAULT_RUNNER = REPO_ROOT / "tools" / "spec2017" / "run_stage_qemu_matrix.py"


@dataclass(frozen=True)
class Suite:
    name: str
    stage: str
    input_set: str
    benches: tuple[str, ...]
    transports: str
    timeout_env: str
    timeout_default: int
    description: str


SPECINT_STAGE_B_BENCHES = (
    "500.perlbench_r",
    "502.gcc_r",
    "505.mcf_r",
    "520.omnetpp_r",
    "523.xalancbmk_r",
    "525.x264_r",
    "531.deepsjeng_r",
    "541.leela_r",
    "557.xz_r",
    "999.specrand_ir",
)

SPECINT_TRAIN_PROMOTION_BENCHES = tuple(
    bench
    for bench in SPECINT_STAGE_B_BENCHES
    if bench not in {"505.mcf_r", "531.deepsjeng_r", "999.specrand_ir"}
)


SUITES: dict[str, Suite] = {
    "test-smoke": Suite(
        name="test-smoke",
        stage="a",
        input_set="test",
        benches=("999.specrand_ir",),
        transports="initramfs",
        timeout_env="SPECINT_TEST_SMOKE_TIMEOUT",
        timeout_default=180,
        description="fast test-input sentinel without refrate cost",
    ),
    "train-smoke": Suite(
        name="train-smoke",
        stage="a",
        input_set="train",
        benches=("999.specrand_ir",),
        transports="initramfs",
        timeout_env="SPECINT_TRAIN_SMOKE_TIMEOUT",
        timeout_default=300,
        description="fast train-input sentinel without refrate cost",
    ),
    "train-cpu-stress": Suite(
        name="train-cpu-stress",
        stage="a",
        input_set="train",
        benches=("531.deepsjeng_r",),
        transports="initramfs",
        timeout_env="SPECINT_TRAIN_CPU_STRESS_TIMEOUT",
        timeout_default=900,
        description="isolated train-input CPU/control-flow stress check",
    ),
    "test-cpu-stress": Suite(
        name="test-cpu-stress",
        stage="a",
        input_set="test",
        benches=("531.deepsjeng_r",),
        transports="initramfs",
        timeout_env="SPECINT_TEST_CPU_STRESS_TIMEOUT",
        timeout_default=900,
        description="isolated test-input CPU/control-flow stress check",
    ),
    "test-vm-stress": Suite(
        name="test-vm-stress",
        stage="a",
        input_set="test",
        benches=("505.mcf_r",),
        transports="initramfs",
        timeout_env="SPECINT_TEST_VM_STRESS_TIMEOUT",
        timeout_default=900,
        description="isolated mcf VM/allocation stress check",
    ),
    "train-vm-stress": Suite(
        name="train-vm-stress",
        stage="a",
        input_set="train",
        benches=("505.mcf_r",),
        transports="initramfs",
        timeout_env="SPECINT_TRAIN_VM_STRESS_TIMEOUT",
        timeout_default=1200,
        description="train-input mcf VM/allocation stress check",
    ),
    "train-promotion": Suite(
        name="train-promotion",
        stage="b",
        input_set="train",
        benches=SPECINT_TRAIN_PROMOTION_BENCHES,
        transports="initramfs",
        timeout_env="SPECINT_TRAIN_PROMOTION_TIMEOUT",
        timeout_default=1800,
        description="nightly train-input SPECint promotion breadth",
    ),
    "train-all": Suite(
        name="train-all",
        stage="b",
        input_set="train",
        benches=SPECINT_STAGE_B_BENCHES,
        transports="initramfs",
        timeout_env="SPECINT_TRAIN_ALL_TIMEOUT",
        timeout_default=180,
        description="bounded all-SPECint train-input diagnostic gate",
    ),
}

PROFILE_SUITES: dict[str, tuple[str, ...]] = {
    "smoke": ("test-smoke",),
    "pr": ("test-smoke", "train-smoke"),
    "train": ("train-all",),
    "nightly": (
        "test-smoke",
        "train-smoke",
        "test-cpu-stress",
        "test-vm-stress",
        "train-cpu-stress",
        "train-vm-stress",
        "train-promotion",
    ),
}


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"error: {name} must be an integer, got {value!r}") from exc


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name, "").strip()
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise SystemExit(f"error: {name} must be a number, got {value!r}") from exc


def _default_qemu() -> str:
    env = os.environ.get("QEMU", "").strip()
    if env:
        return str(Path(os.path.expanduser(env)).resolve())
    qemu = default_qemu_binary(REPO_ROOT)
    return str(qemu.resolve())


def _runner_supports_option(runner: Path, option: str) -> bool:
    try:
        return option in runner.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def _select_suites(profile: str, requested: list[str]) -> list[Suite]:
    names = list(PROFILE_SUITES[profile])
    if requested:
        wanted = set(requested)
        unknown = sorted(wanted - set(SUITES))
        if unknown:
            raise SystemExit(f"error: unknown suite(s): {', '.join(unknown)}")
        names = [name for name in names if name in wanted]
        missing = sorted(wanted - set(names))
        if missing:
            raise SystemExit(
                f"error: suite(s) not enabled by profile {profile}: {', '.join(missing)}"
            )
    return [SUITES[name] for name in names]


def _read_matrix_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"loaded": False, "ok": False, "error": f"missing {path}"}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"loaded": False, "ok": False, "error": str(exc)}
    obj["loaded"] = True
    return obj


def _matrix_failure_classes(matrix: dict[str, Any]) -> dict[str, str]:
    classes: dict[str, str] = {}
    results = matrix.get("results", [])
    if not isinstance(results, list):
        return classes
    for row in results:
        if not isinstance(row, dict):
            continue
        row_classes = row.get("failure_classes", {})
        if not isinstance(row_classes, dict):
            continue
        for bench, cls in row_classes.items():
            classes[str(bench)] = str(cls)
    return classes


def _matrix_failure_details(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    results = matrix.get("results", [])
    if not isinstance(results, list):
        return details
    for row in results:
        if not isinstance(row, dict):
            continue
        row_details = row.get("failure_details", {})
        if not isinstance(row_details, dict):
            continue
        for bench, detail in row_details.items():
            if isinstance(detail, dict):
                details[str(bench)] = detail
    return details


def _format_failure_details(details: dict[str, dict[str, Any]]) -> str:
    if not details:
        return "-"
    parts: list[str] = []
    for bench, row in sorted(details.items()):
        running = "running" if row.get("heartbeat_running") else "not-running"
        site = "site-progress" if row.get("heartbeat_site_progress") else "same-site"
        bpc = row.get("heartbeat_last_bpc") or "no-bpc"
        progress = row.get("heartbeat_last_progress") or "no-progress-tag"
        parts.append(f"{bench}: {running}/{site} {progress} bpc={bpc}")
    return ", ".join(parts)


def _suite_command(
    *,
    suite: Suite,
    runner: Path,
    spec_dir: Path,
    qemu: Path,
    sysroot: Path,
    out_dir: Path,
    append_extra: str,
    heartbeat_sec: float,
    memory_mb: int,
    qemu_heartbeat_interval: int,
    no_progress_timeout: float,
    forward_memory_mb: bool,
    forward_qemu_heartbeat: bool,
    forward_no_progress: bool,
    forward_stack_limit: bool,
    stack_limit: str,
    guest_heartbeat_sec: int,
    dump_prefix_bytes: int,
    transports_override: str,
) -> list[str]:
    timeout = _env_int(suite.timeout_env, suite.timeout_default)
    transports = transports_override or suite.transports
    cmd = [
        sys.executable,
        str(runner),
        "--spec-dir",
        str(spec_dir),
        "--qemu",
        str(qemu),
        "--stage",
        suite.stage,
        "--input-set",
        suite.input_set,
        "--transports",
        transports,
        "--sysroot",
        str(sysroot),
        "--timeout",
        str(timeout),
        "--heartbeat-sec",
        str(heartbeat_sec),
        "--guest-heartbeat-sec",
        str(guest_heartbeat_sec),
        "--append-extra",
        append_extra,
        "--dump-prefix-bytes",
        str(dump_prefix_bytes),
        "--strict",
        "--out-dir",
        str(out_dir / suite.name),
    ]
    if forward_memory_mb:
        cmd.extend(["--memory-mb", str(memory_mb)])
    if forward_qemu_heartbeat:
        cmd.extend(["--qemu-heartbeat-interval", str(qemu_heartbeat_interval)])
    if forward_no_progress:
        cmd.extend(["--no-progress-timeout", str(no_progress_timeout)])
    if stack_limit.strip() and forward_stack_limit:
        cmd.extend(["--stack-limit", stack_limit.strip()])
    for bench in suite.benches:
        cmd.extend(["--bench", bench])
    return cmd


def _write_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# SPECint Fast Gate Summary",
        "",
        "## Run",
        "",
        f"- profile: `{summary['profile']}`",
        f"- ok: `{str(summary['ok']).lower()}`",
        f"- elapsed_sec: `{summary['elapsed_sec']}`",
        f"- qemu: `{summary['qemu']}`",
        f"- spec_dir: `{summary['spec_dir']}`",
        f"- memory_mb: `{summary['memory_mb']}`",
        f"- stack_limit: `{summary['stack_limit']}`",
        "",
        "## Suites",
        "",
        "| Suite | Input | Benches | OK | Return | Elapsed | Failure Classes | Liveness | Summary |",
        "|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for row in summary["suites"]:
        benches = ", ".join(row["benches"])
        failure_classes = row.get("failure_classes", {})
        if isinstance(failure_classes, dict) and failure_classes:
            classes_text = ", ".join(
                f"{bench}: {cls}" for bench, cls in sorted(failure_classes.items())
            )
        else:
            classes_text = "-"
        failure_details = row.get("failure_details", {})
        details_text = _format_failure_details(
            failure_details if isinstance(failure_details, dict) else {}
        )
        lines.append(
            "| "
            f"`{row['name']}` | "
            f"`{row['input_set']}` | "
            f"`{benches}` | "
            f"`{str(row['ok']).lower()}` | "
            f"`{row['returncode']}` | "
            f"`{row['elapsed_sec']}` | "
            f"`{classes_text}` | "
            f"`{details_text}` | "
            f"`{row['matrix_summary']}` |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=sorted(PROFILE_SUITES), default="pr")
    parser.add_argument("--suite", action="append", default=[], help="Run only a named suite enabled by --profile.")
    parser.add_argument("--spec-dir", default=str(DEFAULT_SPEC_DIR))
    parser.add_argument("--runner", default=str(DEFAULT_RUNNER))
    parser.add_argument("--qemu", default=_default_qemu())
    parser.add_argument("--sysroot", default=str(REPO_ROOT / "out" / "libc" / "musl" / "install" / "phase-b"))
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "workloads" / "generated" / "specint-fast-gate"))
    parser.add_argument("--append-extra", default=os.environ.get("SPEC_APPEND_EXTRA", os.environ.get("LINX_SPEC_APPEND_EXTRA", "norandmaps")))
    parser.add_argument("--heartbeat-sec", type=float, default=float(os.environ.get("SPEC_HEARTBEAT_SEC", os.environ.get("LINX_SPEC_HEARTBEAT_SEC", "30"))))
    parser.add_argument("--memory-mb", type=int, default=_env_int("SPEC_MEMORY_MB", _env_int("LINX_SPEC_MEMORY_MB", 2048)))
    parser.add_argument("--qemu-heartbeat-interval", type=int, default=_env_int("SPEC_QEMU_HEARTBEAT_INTERVAL", _env_int("LINX_SPEC_QEMU_HEARTBEAT_INTERVAL", 0)))
    parser.add_argument("--no-progress-timeout", type=float, default=_env_float("SPEC_NO_PROGRESS_TIMEOUT", _env_float("LINX_SPEC_NO_PROGRESS_TIMEOUT", 0.0)))
    parser.add_argument(
        "--stack-limit",
        default=os.environ.get(
            "SPEC_STACK_LIMIT",
            os.environ.get("LINX_SPEC_STACK_LIMIT_BYTES", os.environ.get("LINX_SPEC_STACK_LIMIT", "")),
        ),
        help="SPEC init wrapper stack limit passed through to the matrix runner.",
    )
    parser.add_argument("--guest-heartbeat-sec", type=int, default=_env_int("SPEC_GUEST_HEARTBEAT_SEC", _env_int("LINX_SPEC_GUEST_HEARTBEAT_SEC", 60)))
    parser.add_argument("--dump-prefix-bytes", type=int, default=_env_int("SPEC_DUMP_PREFIX_BYTES", _env_int("LINX_SPEC_DUMP_PREFIX_BYTES", 0)))
    parser.add_argument("--transports", default="", help="Override each suite transport list, e.g. initramfs or 9p,initramfs.")
    parser.add_argument("--continue-on-fail", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.heartbeat_sec < 0:
        raise SystemExit("error: --heartbeat-sec must be >= 0")
    if args.memory_mb <= 0:
        raise SystemExit("error: --memory-mb must be > 0")
    if args.qemu_heartbeat_interval < 0:
        raise SystemExit("error: --qemu-heartbeat-interval must be >= 0")
    if args.no_progress_timeout < 0:
        raise SystemExit("error: --no-progress-timeout must be >= 0")
    if args.guest_heartbeat_sec < 0:
        raise SystemExit("error: --guest-heartbeat-sec must be >= 0")
    if args.dump_prefix_bytes < 0:
        raise SystemExit("error: --dump-prefix-bytes must be >= 0")

    spec_dir = Path(os.path.expanduser(args.spec_dir)).resolve()
    runner = Path(os.path.expanduser(args.runner)).resolve()
    qemu = Path(os.path.expanduser(args.qemu)).resolve()
    sysroot = Path(os.path.expanduser(args.sysroot)).resolve()
    out_dir = Path(os.path.expanduser(args.out_dir)).resolve()

    if not runner.is_file():
        raise SystemExit(f"error: missing SPEC matrix runner: {runner}")
    if not spec_dir.exists():
        raise SystemExit(f"error: missing SPEC dir: {spec_dir}")
    if not qemu.exists():
        raise SystemExit(f"error: missing QEMU binary: {qemu}")

    runner_has_qemu_heartbeat = _runner_supports_option(runner, "--qemu-heartbeat-interval")
    runner_has_no_progress = _runner_supports_option(runner, "--no-progress-timeout")
    runner_has_memory_mb = _runner_supports_option(runner, "--memory-mb")
    runner_has_stack_limit = _runner_supports_option(runner, "--stack-limit")
    if args.qemu_heartbeat_interval and not runner_has_qemu_heartbeat:
        raise SystemExit(
            "error: local SPEC matrix runner does not support "
            "--qemu-heartbeat-interval; update tools/spec2017/run_stage_qemu_matrix.py "
            "or rerun without the heartbeat switch"
        )
    if args.no_progress_timeout and not runner_has_no_progress:
        raise SystemExit(
            "error: local SPEC matrix runner does not support "
            "--no-progress-timeout; update tools/spec2017/run_stage_qemu_matrix.py "
            "or rerun without the no-progress switch"
        )
    if args.memory_mb != 2048 and not runner_has_memory_mb:
        raise SystemExit(
            "error: local SPEC matrix runner does not support "
            "--memory-mb; update tools/spec2017/run_stage_qemu_matrix.py "
            "or rerun with the default memory size"
        )
    if args.stack_limit.strip() and not runner_has_stack_limit:
        raise SystemExit(
            "error: local SPEC matrix runner does not support "
            "--stack-limit; update tools/spec2017/run_stage_qemu_matrix.py "
            "or rerun without the stack-limit switch"
        )

    suites = _select_suites(args.profile, args.suite)
    out_dir.mkdir(parents=True, exist_ok=True)

    started = _utc_now()
    t0 = time.monotonic()
    rows: list[dict[str, Any]] = []
    overall_ok = True

    for suite in suites:
        suite_out = out_dir / suite.name
        cmd = _suite_command(
            suite=suite,
            runner=runner,
            spec_dir=spec_dir,
            qemu=qemu,
            sysroot=sysroot,
            out_dir=out_dir,
            append_extra=args.append_extra,
            heartbeat_sec=args.heartbeat_sec,
            memory_mb=args.memory_mb,
            qemu_heartbeat_interval=args.qemu_heartbeat_interval,
            no_progress_timeout=args.no_progress_timeout,
            forward_memory_mb=runner_has_memory_mb,
            forward_qemu_heartbeat=runner_has_qemu_heartbeat,
            forward_no_progress=runner_has_no_progress,
            forward_stack_limit=runner_has_stack_limit,
            stack_limit=args.stack_limit,
            guest_heartbeat_sec=args.guest_heartbeat_sec,
            dump_prefix_bytes=args.dump_prefix_bytes,
            transports_override=args.transports,
        )
        print(f"-- {suite.name}: {suite.description}")
        print(" ".join(cmd))
        suite_start = time.monotonic()
        if args.dry_run:
            rc = 0
            matrix = {"ok": True, "loaded": False, "dry_run": True}
        else:
            proc = subprocess.run(cmd, check=False)
            rc = proc.returncode
            matrix = _read_matrix_summary(suite_out / "qemu_matrix_summary.json")
        row_ok = rc == 0 and bool(matrix.get("ok", False))
        failure_classes = _matrix_failure_classes(matrix)
        failure_details = _matrix_failure_details(matrix)
        rows.append(
            {
                "name": suite.name,
                "description": suite.description,
                "stage": suite.stage,
                "input_set": suite.input_set,
                "benches": list(suite.benches),
                "transports": args.transports or suite.transports,
                "timeout_sec": _env_int(suite.timeout_env, suite.timeout_default),
                "command": cmd,
                "returncode": rc,
                "ok": row_ok,
                "elapsed_sec": round(time.monotonic() - suite_start, 3),
                "out_dir": str(suite_out),
                "matrix_summary": str(suite_out / "qemu_matrix_summary.json"),
                "matrix_loaded": bool(matrix.get("loaded", False)),
                "matrix_ok": bool(matrix.get("ok", False)),
                "failure_classes": failure_classes,
                "failure_details": failure_details,
            }
        )
        overall_ok = overall_ok and row_ok
        if not row_ok and not args.continue_on_fail:
            break

    summary = {
        "schema_version": "linx-specint-fast-gate-v1",
        "profile": args.profile,
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
        "elapsed_sec": round(time.monotonic() - t0, 3),
        "dry_run": bool(args.dry_run),
        "ok": overall_ok,
        "spec_dir": str(spec_dir),
        "qemu": str(qemu),
        "sysroot": str(sysroot),
        "memory_mb": args.memory_mb,
        "append_extra": args.append_extra,
        "stack_limit": args.stack_limit.strip() or "default",
        "qemu_heartbeat_interval": args.qemu_heartbeat_interval,
        "no_progress_timeout": args.no_progress_timeout,
        "guest_heartbeat_sec": args.guest_heartbeat_sec,
        "suites": rows,
    }
    summary_json = out_dir / "specint_fast_gate_summary.json"
    summary_md = out_dir / "specint_fast_gate_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(summary_md, summary)
    print(f"summary_json={summary_json}")
    print(f"summary_md={summary_md}")
    print(f"ok={str(overall_ok).lower()}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
