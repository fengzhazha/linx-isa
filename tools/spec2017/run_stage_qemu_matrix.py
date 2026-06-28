#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
RUNNER = SCRIPT_DIR / "run_int_rate_qemu.py"


def _default_qemu() -> str:
    env = os.environ.get("QEMU", "").strip()
    if env:
        return str(Path(os.path.expanduser(env)).resolve())
    qemu_root = REPO_ROOT / "emulator" / "qemu"
    for rel in ("build-linx", "build-tci", "build"):
        candidate = qemu_root / rel / "qemu-system-linx64"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
    return str((qemu_root / "build-linx" / "qemu-system-linx64").resolve())


def _default_musl_sysroot() -> str:
    env = os.environ.get("LINX_SYSROOT", "").strip()
    if env:
        return str(Path(os.path.expanduser(env)).resolve())
    phase_c = REPO_ROOT / "out" / "libc" / "musl" / "install" / "phase-c"
    if _usable_static_sysroot(phase_c):
        return str(phase_c.resolve())
    return str((REPO_ROOT / "out" / "libc" / "musl" / "install" / "phase-b").resolve())


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


def _usable_static_sysroot(path: Path) -> bool:
    return (
        (path / "usr" / "include" / "errno.h").is_file()
        and (path / "lib" / "libc.a").is_file()
        and (
            (path / "lib" / "rcrt1.o").is_file()
            or (path / "lib" / "crt1.o").is_file()
        )
    )


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _parse_transports(value: str) -> list[str]:
    items = [x.strip() for x in value.split(",") if x.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in {"9p", "initramfs"}:
            raise SystemExit(f"error: unsupported transport '{item}' (expected 9p/initramfs)")
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    if not out:
        raise SystemExit("error: --transports resolved to empty set")
    return out


def _default_transports(stage: str) -> list[str]:
    return ["9p", "initramfs"] if stage == "a" else ["9p"]


def _transport_failed_benches(summary_obj: dict[str, Any]) -> list[str]:
    results = summary_obj.get("results", {})
    if not isinstance(results, dict):
        return []
    failed: list[str] = []
    for bench, bench_result in sorted(results.items()):
        ok = isinstance(bench_result, dict) and bool(bench_result.get("ok", False))
        if not ok:
            failed.append(str(bench))
    return failed


def _transport_failure_classes(summary_obj: dict[str, Any]) -> dict[str, str]:
    results = summary_obj.get("results", {})
    if not isinstance(results, dict):
        return {}

    classes: dict[str, str] = {}
    for bench, bench_result in sorted(results.items()):
        if not isinstance(bench_result, dict) or bool(bench_result.get("ok", False)):
            continue
        qemu_runs = bench_result.get("qemu", [])
        if not isinstance(qemu_runs, list) or not qemu_runs:
            if bench_result.get("error"):
                classes[str(bench)] = "runner-error"
            continue
        first_run = qemu_runs[0]
        if isinstance(first_run, dict):
            classes[str(bench)] = str(first_run.get("failure_class") or "unclassified")
    return classes


def _write_md(path: Path, summary: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# SPEC QEMU Matrix Summary")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- stage: `{summary['stage']}`")
    lines.append(f"- input_set: `{summary['input_set']}`")
    lines.append(f"- strict: `{str(summary['strict']).lower()}`")
    lines.append(f"- transports: `{', '.join(summary['transports'])}`")
    lines.append(f"- timeout_sec: `{summary['timeout_sec']}`")
    lines.append(f"- append_extra: `{summary['append_extra'] or '-'}`")
    lines.append(f"- guest_heartbeat_sec: `{summary['guest_heartbeat_sec']}`")
    if summary.get("bench_override"):
        benches = ", ".join(summary["bench_override"])
        lines.append(f"- bench_override: `{benches}`")
    lines.append(f"- ok: `{str(summary['ok']).lower()}`")
    lines.append(f"- elapsed_sec: `{summary['elapsed_sec']}`")
    lines.append("")
    lines.append("## Transport Results")
    lines.append("")
    lines.append("| Transport | OK | Return | Failed Benches | Failure Classes | Summary | Log |")
    lines.append("|---|---:|---:|---|---|---|---|")

    for row in summary.get("results", []):
        failed_benches = row.get("failed_benches", [])
        failed_text = ", ".join(failed_benches) if failed_benches else "-"
        failure_classes = row.get("failure_classes", {})
        if isinstance(failure_classes, dict) and failure_classes:
            classes_text = ", ".join(
                f"{bench}: {cls}" for bench, cls in sorted(failure_classes.items())
            )
        else:
            classes_text = "-"
        lines.append(
            "| "
            f"`{row.get('transport', '')}` | "
            f"`{str(bool(row.get('ok', False))).lower()}` | "
            f"`{row.get('returncode', 'n/a')}` | "
            f"`{failed_text}` | "
            f"`{classes_text}` | "
            f"`{row.get('summary_json', '')}` | "
            f"`{row.get('log', '')}` |"
        )

    lines.append("")
    if summary.get("failed_transports"):
        lines.append("## Failed Transports")
        lines.append("")
        for item in summary["failed_transports"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("## Failed Transports")
        lines.append("")
        lines.append("- none")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Run SPEC stage matrix across QEMU transports.")
    ap.add_argument(
        "--spec-dir",
        default=str(REPO_ROOT / "workloads" / "spec2017" / "cpu2017v118_x64_gcc12_avx2"),
    )
    ap.add_argument(
        "--qemu",
        default=_default_qemu(),
        help="QEMU binary passed through to the per-transport runner.",
    )
    ap.add_argument("--stage", choices=("a", "b"), default="a")
    ap.add_argument("--input-set", choices=("refrate", "test", "train"), default="test")
    ap.add_argument(
        "--transports",
        default="",
        help="Comma-separated transport list. Defaults: stage-a=9p,initramfs; stage-b=9p.",
    )
    ap.add_argument("--bench", action="append", help="Optional bench override; repeatable.")
    ap.add_argument("--strict", action="store_true", help="Fail if any transport/bench fails.")
    ap.add_argument("--sysroot", default=_default_musl_sysroot(), help="Linx sysroot passed through to the per-transport runner.")
    ap.add_argument(
        "--timeout",
        type=int,
        default=_env_int("LINX_SPEC_QEMU_TIMEOUT", 1200),
        help="Per-transport runner timeout in seconds (default: LINX_SPEC_QEMU_TIMEOUT or 1200).",
    )
    ap.add_argument(
        "--heartbeat-sec",
        type=float,
        default=_env_float("LINX_SPEC_HEARTBEAT_SEC", 30.0),
        help="Host heartbeat interval passed through to the per-transport runner (0 disables).",
    )
    ap.add_argument(
        "--qemu-heartbeat-interval",
        type=int,
        default=_env_int("LINX_SPEC_QEMU_HEARTBEAT_INTERVAL", 0),
        help="QEMU BPC heartbeat interval passed through to the per-transport runner (0 disables).",
    )
    ap.add_argument(
        "--no-progress-timeout",
        type=float,
        default=_env_float("LINX_SPEC_NO_PROGRESS_TIMEOUT", 0.0),
        help="Fail a per-benchmark QEMU run if QEMU emits no output for this many seconds (0 disables).",
    )
    ap.add_argument(
        "--guest-heartbeat-sec",
        type=int,
        default=_env_int("LINX_SPEC_GUEST_HEARTBEAT_SEC", 0),
        help="Guest child/output heartbeat interval passed through to the initramfs runner (0 disables).",
    )
    ap.add_argument(
        "--append-extra",
        default=os.environ.get("LINX_SPEC_APPEND_EXTRA", ""),
        help="Extra kernel command-line text passed through to the per-transport runner.",
    )
    ap.add_argument(
        "--dump-prefix-bytes",
        type=int,
        default=_env_int("LINX_SPEC_DUMP_PREFIX_BYTES", 0),
        help="Emit first N verified output bytes in initramfs mode (0 disables).",
    )
    ap.add_argument(
        "--out-dir",
        default="",
        help="Output directory for matrix logs/summaries (default: <spec-dir>/tmp/linx-qemu-matrix/stage_<stage>).",
    )
    args = ap.parse_args(argv)

    spec_dir = Path(os.path.expanduser(args.spec_dir)).resolve()
    if not (spec_dir / "benchspec" / "CPU").is_dir():
        raise SystemExit(f"error: invalid SPEC dir: {spec_dir}")
    if not RUNNER.is_file():
        raise SystemExit(f"error: missing runner: {RUNNER}")
    if args.timeout <= 0:
        raise SystemExit("error: --timeout must be > 0")
    if args.heartbeat_sec < 0:
        raise SystemExit("error: --heartbeat-sec must be >= 0")
    if args.qemu_heartbeat_interval < 0:
        raise SystemExit("error: --qemu-heartbeat-interval must be >= 0")
    if args.no_progress_timeout < 0:
        raise SystemExit("error: --no-progress-timeout must be >= 0")
    if args.guest_heartbeat_sec < 0:
        raise SystemExit("error: --guest-heartbeat-sec must be >= 0")
    if args.dump_prefix_bytes < 0:
        raise SystemExit("error: --dump-prefix-bytes must be >= 0")

    transports = _parse_transports(args.transports) if args.transports else _default_transports(args.stage)
    benches = list(args.bench or [])
    if args.out_dir:
        out_dir = Path(os.path.expanduser(args.out_dir)).resolve()
    else:
        out_dir = spec_dir / "tmp" / "linx-qemu-matrix" / f"stage_{args.stage}"
    out_dir.mkdir(parents=True, exist_ok=True)

    started = _utc_now()
    t0 = time.monotonic()

    results: list[dict[str, Any]] = []
    failed_transports: list[str] = []

    for transport in transports:
        transport_out = out_dir / transport
        transport_out.mkdir(parents=True, exist_ok=True)
        log_path = transport_out / f"stage_{args.stage}_{transport}.log"
        runner_summary = transport_out / f"stage_{args.stage}_summary.json"

        cmd = [
            sys.executable,
            str(RUNNER),
            "--spec-dir",
            str(spec_dir),
            "--qemu",
            str(Path(os.path.expanduser(args.qemu)).resolve()),
            "--stage",
            args.stage,
            "--transport",
            transport,
            "--input-set",
            args.input_set,
            "--sysroot",
            str(Path(os.path.expanduser(args.sysroot)).resolve()),
            "--out-dir",
            str(transport_out),
            "--timeout",
            str(args.timeout),
            "--heartbeat-sec",
            str(args.heartbeat_sec),
            "--qemu-heartbeat-interval",
            str(args.qemu_heartbeat_interval),
            "--no-progress-timeout",
            str(args.no_progress_timeout),
            "--guest-heartbeat-sec",
            str(args.guest_heartbeat_sec),
            "--append-extra",
            args.append_extra,
            "--dump-prefix-bytes",
            str(args.dump_prefix_bytes),
        ]
        for bench in benches:
            cmd.extend(["--bench", bench])

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        log_path.write_bytes(proc.stdout)

        summary_obj: dict[str, Any] = {}
        summary_loaded = False
        if runner_summary.is_file():
            try:
                summary_obj = json.loads(runner_summary.read_text(encoding="utf-8"))
                summary_loaded = True
            except json.JSONDecodeError:
                summary_obj = {}

        failed_benches = _transport_failed_benches(summary_obj) if summary_loaded else []
        failure_classes = _transport_failure_classes(summary_obj) if summary_loaded else {}
        transport_ok = bool(summary_obj.get("ok", False)) if summary_loaded else False

        row = {
            "transport": transport,
            "command": cmd,
            "returncode": proc.returncode,
            "ok": bool(transport_ok),
            "summary_loaded": summary_loaded,
            "summary_json": str(runner_summary),
            "log": str(log_path),
            "out_dir": str(transport_out),
            "failed_benches": failed_benches,
            "failure_classes": failure_classes,
        }
        results.append(row)
        if not row["ok"]:
            failed_transports.append(transport)

    overall_ok = len(failed_transports) == 0
    summary = {
        "schema_version": "linx-spec-qemu-matrix-v1",
        "stage": args.stage,
        "input_set": args.input_set,
        "strict": bool(args.strict),
        "spec_dir": str(spec_dir),
        "transports": transports,
        "timeout_sec": int(args.timeout),
        "heartbeat_sec": float(args.heartbeat_sec),
        "qemu_heartbeat_interval": int(args.qemu_heartbeat_interval),
        "no_progress_timeout": float(args.no_progress_timeout),
        "guest_heartbeat_sec": int(args.guest_heartbeat_sec),
        "append_extra": str(args.append_extra),
        "dump_prefix_bytes": int(args.dump_prefix_bytes),
        "bench_override": benches,
        "started_at_utc": started,
        "finished_at_utc": _utc_now(),
        "elapsed_sec": round(time.monotonic() - t0, 3),
        "ok": overall_ok,
        "failed_transports": failed_transports,
        "results": results,
    }

    summary_json = out_dir / "qemu_matrix_summary.json"
    summary_md = out_dir / "qemu_matrix_summary.md"
    summary_json.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(summary_md, summary)

    print(f"summary_json={summary_json}")
    print(f"summary_md={summary_md}")
    print(f"ok={str(overall_ok).lower()} strict={int(bool(args.strict))}")

    if args.strict and not overall_ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
