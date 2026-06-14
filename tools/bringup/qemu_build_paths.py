"""Shared QEMU binary selection for bring-up runners."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _qemu_head(root: Path) -> str | None:
    qemu_root = root / "emulator" / "qemu"
    try:
        return subprocess.check_output(
            ["git", "-C", str(qemu_root), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _matching_clean_qemu(root: Path, target: str = "qemu-system-linx64") -> Path | None:
    out_dir = Path(os.environ.get("QEMU_CLEAN_OUT_DIR", "/tmp/linx-qemu-clean-build"))
    binary = out_dir / target
    marker = out_dir / ".linx_qemu_clean_head"
    if not binary.is_file() or not os.access(binary, os.X_OK) or not marker.is_file():
        return None

    head = _qemu_head(root)
    if head is None:
        return None

    marker_head = marker.read_text(encoding="utf-8", errors="replace").strip().split(":", 1)[0]
    if marker_head != head:
        return None
    return binary


def default_qemu_binary(root: Path, target: str = "qemu-system-linx64") -> Path:
    clean = _matching_clean_qemu(root, target=target)
    if clean is not None:
        return clean
    return root / "emulator" / "qemu" / "build" / target
