#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
LINUX_INITRAMFS_DIR = REPO_ROOT / "kernel" / "linux" / "tools" / "linxisa" / "initramfs"


def _run(script_name: str, env: dict[str, str]) -> int:
    script = LINUX_INITRAMFS_DIR / script_name
    if not script.exists():
        raise SystemExit(f"error: missing proof script: {script}")
    return subprocess.run([sys.executable, str(script)], env=env, check=False).returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Run the canonical Linx Linux-on-QEMU boot proof scripts."
    )
    parser.add_argument(
        "--userspace-only",
        action="store_true",
        help="Run only the userspace-entry proof (tinytrap + semihost exit).",
    )
    parser.add_argument(
        "--poweroff-only",
        action="store_true",
        help="Run only the native poweroff proof (tiny PID1 -> kernel poweroff).",
    )
    args = parser.parse_args(argv)

    if args.userspace_only and args.poweroff_only:
        raise SystemExit("error: --userspace-only and --poweroff-only are mutually exclusive")

    env = os.environ.copy()
    results: list[tuple[str, int]] = []

    if not args.poweroff_only:
        results.append(("userspace", _run("boot_userspace_proof.py", env)))
    if not args.userspace_only:
        results.append(("poweroff", _run("boot_poweroff_proof.py", env)))

    failures = [name for name, rc in results if rc != 0]
    if failures:
        sys.stderr.write("error: linux boot proof failure in " + ", ".join(failures) + "\n")
        return 1

    print("ok: linux boot proof suite passed")
    for name, _ in results:
        print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
