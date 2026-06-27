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
        timeout_default=300,
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
        benches=(
            "500.perlbench_r",
            "502.gcc_r",
            "520.omnetpp_r",
            "523.xalancbmk_r",
            "525.x264_r",
            "541.leela_r",
            "557.xz_r",
        ),
        transports="initramfs",
        timeout_env="SPECINT_TRAIN_PROMOTION_TIMEOUT",
        timeout_default=1800,
        description="nightly train-input SPECint promotion breadth",
    ),
}

PROFILE_SUITES: dict[str, tuple[str, ...]] = {
    "smoke": ("test-smoke",),
    "pr": ("test-smoke", "train-smoke"),
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


def _default_qemu() -> str:
    env = os.environ.get("QEMU", "").strip()
    if env:
        return str(Path(os.path.expanduser(env)).resolve())
    qemu = default_qemu_binary(REPO_ROOT)
    return str(qemu.resolve())


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
        "",
        "## Suites",
        "",
        "| Suite | Input | Benches | OK | Return | Elapsed | Summary |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in summary["suites"]:
        benches = ", ".join(row["benches"])
        lines.append(
            "| "
            f"`{row['name']}` | "
            f"`{row['input_set']}` | "
            f"`{benches}` | "
            f"`{str(row['ok']).lower()}` | "
            f"`{row['returncode']}` | "
            f"`{row['elapsed_sec']}` | "
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
    parser.add_argument("--guest-heartbeat-sec", type=int, default=_env_int("SPEC_GUEST_HEARTBEAT_SEC", _env_int("LINX_SPEC_GUEST_HEARTBEAT_SEC", 60)))
    parser.add_argument("--dump-prefix-bytes", type=int, default=_env_int("SPEC_DUMP_PREFIX_BYTES", _env_int("LINX_SPEC_DUMP_PREFIX_BYTES", 0)))
    parser.add_argument("--transports", default="", help="Override each suite transport list, e.g. initramfs or 9p,initramfs.")
    parser.add_argument("--continue-on-fail", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.heartbeat_sec < 0:
        raise SystemExit("error: --heartbeat-sec must be >= 0")
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
        "append_extra": args.append_extra,
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
