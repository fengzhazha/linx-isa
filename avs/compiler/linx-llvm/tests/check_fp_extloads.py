#!/usr/bin/env python3
"""Reject raw f32 constant loads that directly feed f64 compares."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


LOAD32_RE = re.compile(r"\b(?:hl\.)?lwu(?:\.pcr)?\b", re.IGNORECASE)
FCMP64_RE = re.compile(r"\bf(?:eq|lt|ge)\.fd\b", re.IGNORECASE)


def is_code_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped and not stripped.startswith(("#", ".", "//")))


def previous_code_line(lines: list[str], index: int) -> tuple[int, str] | None:
    for prev in range(index - 1, -1, -1):
        if is_code_line(lines[prev]):
            return prev + 1, lines[prev].rstrip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asm", required=True, type=Path)
    parser.add_argument("--label", default="floating-point")
    args = parser.parse_args()

    lines = args.asm.read_text(encoding="utf-8").splitlines()
    failures: list[str] = []
    for idx, line in enumerate(lines):
        if not FCMP64_RE.search(line):
            continue
        prev = previous_code_line(lines, idx)
        if prev is None:
            continue
        prev_line_no, prev_line = prev
        if LOAD32_RE.search(prev_line):
            failures.append(
                f"{args.asm}:{prev_line_no}: raw 32-bit load feeds "
                f"64-bit compare at line {idx + 1}: {prev_line}"
            )

    if failures:
        print(f"error: {args.label}: invalid f32 extload before f64 compare", file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
