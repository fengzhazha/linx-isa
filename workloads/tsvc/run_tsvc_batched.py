#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import run_tsvc as core


def _exact_kernel_regex(kernels: list[str]) -> str:
    return "^(" + "|".join(re.escape(k) for k in kernels) + ")$"


def _resolve_kernel_list(tsvc_src_arg: str | None,
                         kernel_regex: str | None) -> tuple[Path, list[str]]:
    src_dir = core._resolve_tsvc_src(tsvc_src_arg)
    tsvc_c = src_dir / "tsvc.c"
    kernels = core._extract_kernel_names(tsvc_c.read_text(encoding="utf-8"))
    if kernel_regex:
        pat = re.compile(kernel_regex)
        kernels = [k for k in kernels if pat.search(k)]
        if not kernels:
            raise SystemExit(f"error: --kernel-regex matched 0 kernels: {kernel_regex}")
    return src_dir, kernels


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_rows(stdout_path: Path) -> dict[str, str]:
    rows = core._parse_kernel_checksums(
        stdout_path.read_text(encoding="utf-8", errors="replace"),
        expected_kernels=[],
    )
    return rows


def _run_batch(python: str,
               base_args: list[str],
               mode: str,
               src_dir: Path,
               batch_out: Path,
               kernels: list[str],
               verbose: bool) -> dict[str, object]:
    cmd = [
        python,
        str(core.TSVC_DIR / "run_tsvc.py"),
        *base_args,
        "--vector-mode",
        mode,
        "--tsvc-src",
        str(src_dir),
        "--kernel-regex",
        _exact_kernel_regex(kernels),
        "--out-dir",
        str(batch_out),
    ]
    if verbose:
        print("+", " ".join(shlex.quote(c) for c in cmd), file=sys.stderr)
    p = subprocess.run(cmd, check=False)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

    reports_dir = batch_out / "reports" / "tsvc"
    qemu_dir = batch_out / "qemu" / "tsvc"
    coverage = _read_json(reports_dir / "vectorization_coverage.json")
    gate = _read_json(reports_dir / "gate_result.json")
    stdout_path = qemu_dir / f"tsvc.{mode}.stdout.txt"
    stderr_path = qemu_dir / f"tsvc.{mode}.stderr.txt"
    return {
        "kernels": kernels,
        "coverage": coverage,
        "gate": gate,
        "stdout_path": stdout_path,
        "stderr_path": stderr_path,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Run TSVC in deterministic kernel batches and aggregate results."
    )
    ap.add_argument("--batch-size", type=int, default=20,
                    help="Number of kernels per batch.")
    ap.add_argument("--kernel-regex", default=None,
                    help="Optional regex to pre-filter kernels before batching.")
    ap.add_argument("--out-dir", required=True,
                    help="Aggregate output root.")
    ap.add_argument("--strict-fail-under", type=int, default=None,
                    help="Aggregate vectorized-kernel floor.")
    ap.add_argument("--tsvc-src", default=None,
                    help="TSVC source directory.")
    ap.add_argument("--vector-mode", choices=("off", "mseq", "mpar", "auto"),
                    default="auto")
    ap.add_argument("--verbose", "-v", action="store_true")
    args, passthrough = ap.parse_known_args(argv)

    if args.batch_size <= 0:
        raise SystemExit("error: --batch-size must be > 0")

    out_root = Path(os.path.expanduser(args.out_dir)).resolve()
    batch_root = out_root / "batches"
    reports_dir = out_root / "reports" / "tsvc"
    qemu_dir = out_root / "qemu" / "tsvc"
    for d in (batch_root, reports_dir, qemu_dir):
        d.mkdir(parents=True, exist_ok=True)

    src_dir, kernels = _resolve_kernel_list(args.tsvc_src, args.kernel_regex)
    batches = [
        kernels[i:i + args.batch_size]
        for i in range(0, len(kernels), args.batch_size)
    ]
    python = sys.executable or "python3"

    merged_rows: list[str] = ["Loop \tTime(sec) \tChecksum"]
    merged_stderr: list[str] = []
    vectorized = 0
    total = 0
    batch_payloads: list[dict[str, object]] = []

    for idx, batch in enumerate(batches, start=1):
        batch_out = batch_root / f"batch_{idx:03d}"
        payload = _run_batch(
            python=python,
            base_args=passthrough,
            mode=args.vector_mode,
            src_dir=src_dir,
            batch_out=batch_out,
            kernels=batch,
            verbose=args.verbose,
        )
        coverage = payload["coverage"]
        vectorized += int(coverage.get("vectorized", 0))
        total += int(coverage.get("total", 0))
        stdout_path = payload["stdout_path"]
        stderr_path = payload["stderr_path"]
        stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        stdout_lines = stdout_text.splitlines()
        for line in stdout_lines:
            if line.startswith("Loop") or line.startswith("Time"):
                continue
            if line.strip():
                merged_rows.append(line)
        stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
        if stderr_text.strip():
            merged_stderr.append(f"# batch {idx:03d}")
            merged_stderr.append(stderr_text.rstrip())
        batch_payloads.append(
            {
                "batch_index": idx,
                "kernel_count": len(batch),
                "kernels": batch,
                "out_dir": str(batch_out),
                "vectorized": int(coverage.get("vectorized", 0)),
                "total": int(coverage.get("total", 0)),
            }
        )

    merged_stdout_path = qemu_dir / f"tsvc.{args.vector_mode}.stdout.txt"
    merged_stderr_path = qemu_dir / f"tsvc.{args.vector_mode}.stderr.txt"
    merged_stdout_path.write_text("\n".join(merged_rows) + "\n", encoding="utf-8")
    merged_stderr_path.write_text(
        ("\n\n".join(merged_stderr) + "\n") if merged_stderr else "",
        encoding="utf-8",
    )

    aggregate = {
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tool": "workloads/tsvc/run_tsvc_batched.py",
        "command": " ".join(
            [shlex.quote(python), "workloads/tsvc/run_tsvc_batched.py",
             *[shlex.quote(a) for a in argv]]
        ),
        "vector_mode": args.vector_mode,
        "batch_size": args.batch_size,
        "kernel_count": len(kernels),
        "vectorized": vectorized,
        "total": total,
        "strict_fail_under": args.strict_fail_under,
        "source": str(src_dir),
        "batches": batch_payloads,
        "sha_manifest": core._build_sha_manifest(),
        "merged_qemu_stdout": str(merged_stdout_path),
        "merged_qemu_stderr": str(merged_stderr_path),
    }

    gate_json = reports_dir / "gate_result.json"
    coverage_json = reports_dir / "vectorization_coverage.json"
    coverage_md = reports_dir / "vectorization_coverage.md"
    kernel_list_path = reports_dir / "kernel_list.txt"
    gate_json.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    coverage_json.write_text(
        json.dumps({"vectorized": vectorized, "total": total}, indent=2) + "\n",
        encoding="utf-8",
    )
    coverage_md.write_text(
        f"# TSVC batched coverage\n\n- Vectorized: `{vectorized}`\n- Total: `{total}`\n",
        encoding="utf-8",
    )
    kernel_list_path.write_text("\n".join(kernels) + "\n", encoding="utf-8")

    report_lines = [
        "# TSVC batched report",
        "",
        f"- Source: `{src_dir}`",
        f"- Vector mode: `{args.vector_mode}`",
        f"- Batch size: `{args.batch_size}`",
        f"- Kernel count: `{len(kernels)}`",
        f"- Vectorized: `{vectorized}/{total}`",
        f"- Merged QEMU stdout: `{merged_stdout_path}`",
        f"- Merged QEMU stderr: `{merged_stderr_path}`",
        f"- Aggregate gate JSON: `{gate_json}`",
    ]
    (out_root / "tsvc_report.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )

    if args.strict_fail_under is not None and vectorized < args.strict_fail_under:
        raise SystemExit(
            f"error: aggregate vectorized kernels {vectorized} below floor "
            f"{args.strict_fail_under}"
        )

    print(f"ok: TSVC {args.vector_mode} batched artifacts generated under {out_root}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
