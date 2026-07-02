#!/usr/bin/env python3
"""Build 502.gcc_r probe binaries with selected objects compiled differently.

The normal SPEC build wrapper applies one OPTIMIZE value to the whole
benchmark.  This helper keeps the default 502 build as the baseline, compiles a
small set of selected objects with extra flags such as -fwrapv, relinks one
probe executable, stages it for the existing QEMU runner, then restores the
build directory objects.  Use the restore subcommand after the QEMU run to put
the default executable back in the SPEC exe directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_DIR = ROOT / "workloads/spec2017/cpu2017v118_x64_gcc12_avx2"
BENCH = "502.gcc_r"
BUILD_REL = Path("benchspec/CPU") / BENCH / "build/build_base_mytest-m64.0000"
EXE_REL = Path("benchspec/CPU") / BENCH / "exe/cpugcc_r_base.mytest-m64"
BUILD_EXE_NAME = "cpugcc_r"
DEFAULT_BASE_OPTIMIZE = "-O0 -fno-vectorize -fno-slp-vectorize"
DEFAULT_EXTRA_FLAGS = "-fwrapv"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str], log: Path) -> None:
    with log.open("a", encoding="utf-8") as f:
        f.write("$ " + " ".join(cmd) + "\n")
        f.flush()
        subprocess.run(cmd, cwd=cwd, env=env, stdout=f, stderr=subprocess.STDOUT, check=True)


def _make_bin() -> str:
    configured = os.environ.get("MAKE", "")
    if configured:
        return configured
    if sys.platform == "darwin" and shutil.which("gmake"):
        return "gmake"
    return "make"


def _parse_sources(makefile: Path) -> list[str]:
    text = makefile.read_text(encoding="utf-8", errors="replace").splitlines()
    collecting = False
    chunks: list[str] = []
    for line in text:
        if not collecting:
            if line.startswith("SOURCES="):
                collecting = True
                chunks.append(line.split("=", 1)[1])
                if not line.rstrip().endswith("\\"):
                    break
            continue
        if line and not line.startswith((" ", "\t")):
            break
        chunks.append(line)
        if not line.rstrip().endswith("\\"):
            break

    if not chunks:
        raise SystemExit(f"error: failed to find SOURCES in {makefile}")

    joined = " ".join(part.rstrip().rstrip("\\") for part in chunks)
    return [token for token in joined.split() if token.endswith(".c")]


def _source_to_object(src: str) -> str:
    return str(Path(src).with_suffix(".o"))


def _object_map(build_dir: Path) -> dict[str, str]:
    sources = _parse_sources(build_dir / "Makefile.spec")
    return {_source_to_object(src): src for src in sources}


def _normalize_object(value: str, object_to_source: dict[str, str]) -> str:
    value = value.strip()
    if not value:
        raise SystemExit("error: empty object name")
    if value.endswith(".c"):
        value = _source_to_object(value)
    elif not value.endswith(".o"):
        value = f"{value}.o"

    path_value = str(Path(value))
    if path_value in object_to_source:
        return path_value

    matches = [obj for obj in object_to_source if Path(obj).name == path_value]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SystemExit(f"error: ambiguous object {value!r}; matches {matches}")
    raise SystemExit(f"error: unknown 502 object {value!r}")


def _split_objects(values: list[str], object_to_source: dict[str, str]) -> list[str]:
    raw: list[str] = []
    for value in values:
        raw.extend(part for part in value.replace(",", " ").split() if part)
    normalized: list[str] = []
    seen: set[str] = set()
    for value in raw:
        obj = _normalize_object(value, object_to_source)
        if obj not in seen:
            seen.add(obj)
            normalized.append(obj)
    if not normalized:
        raise SystemExit("error: at least one object is required")
    return normalized


def _common_env(args: argparse.Namespace) -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("LINX_SYSROOT", str((ROOT / f"out/libc/musl/install/{args.mode}").resolve()))
    env.setdefault("LINX_SPEC_COMPAT_INCLUDE", str((ROOT / "tools/spec2017/compat").resolve()))
    env.setdefault("LINX_SPEC_FORCE_STATIC", "1")
    env.setdefault("LINX_SPEC_LINK_MODE", "default")
    return env


def _make_args(args: argparse.Namespace, optimize: str) -> list[str]:
    cc = str((ROOT / "tools/spec2017/linx_cc.sh").resolve())
    cxx = str((ROOT / "tools/spec2017/linx_cxx.sh").resolve())
    return [
        f"SPEC={args.spec_dir}",
        f"CC={cc}",
        f"CXX={cxx}",
        f"LD={cc}",
        f"CLD={cc}",
        f"CXXLD={cxx}",
        "FC=false",
        "SPECLANG=",
        f"OPTIMIZE={optimize}",
        "EXTRA_OPTIMIZE=",
        "EXTRA_COPTIMIZE=",
        "EXTRA_CXXOPTIMIZE=",
        "PORTABILITY=",
        "EXTRA_PORTABILITY=",
    ]


def _stage(args: argparse.Namespace) -> None:
    args.spec_dir = Path(args.spec_dir).resolve()
    build_dir = args.spec_dir / BUILD_REL
    exe_path = args.spec_dir / EXE_REL
    build_exe = build_dir / BUILD_EXE_NAME
    if not build_dir.is_dir():
        raise SystemExit(f"error: missing 502 build dir: {build_dir}")
    if not exe_path.is_file():
        raise SystemExit(f"error: missing default staged 502 executable: {exe_path}")
    if not build_exe.is_file():
        raise SystemExit(f"error: missing default build executable: {build_exe}")

    object_to_source = _object_map(build_dir)
    objects = _split_objects(args.objects, object_to_source)
    out_dir = Path(args.out_dir).resolve()
    backup_dir = out_dir / "default-backup"
    variant_dir = out_dir / "variant"
    mixed_object_dir = variant_dir / "mixed-objects"
    log = out_dir / "probe_502_mixed_flags.log"
    manifest_path = out_dir / "mixed_flags_manifest.json"
    out_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    variant_dir.mkdir(parents=True, exist_ok=True)
    mixed_object_dir.mkdir(parents=True, exist_ok=True)

    if manifest_path.exists() and not args.force:
        raise SystemExit(f"error: manifest already exists; pass --force to replace: {manifest_path}")

    for old in (log, manifest_path):
        if old.exists():
            old.unlink()

    selected: list[dict[str, Any]] = []
    restore_paths: list[tuple[Path, Path]] = []
    for obj in objects:
        src = object_to_source[obj]
        obj_path = build_dir / obj
        if not obj_path.is_file():
            raise SystemExit(f"error: missing baseline object: {obj_path}")
        backup_obj = backup_dir / obj
        backup_obj.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(obj_path, backup_obj)
        restore_paths.append((backup_obj, obj_path))
        selected.append(
            {
                "object": obj,
                "source": src,
                "baseline_object": str(obj_path),
                "baseline_sha256": _sha256(obj_path),
                "backup": str(backup_obj),
            }
        )

    backup_build_exe = backup_dir / BUILD_EXE_NAME
    backup_staged_exe = backup_dir / EXE_REL.name
    shutil.copy2(build_exe, backup_build_exe)
    shutil.copy2(exe_path, backup_staged_exe)
    restore_paths.extend([(backup_build_exe, build_exe)])

    make = _make_bin()
    env = _common_env(args)
    base_optimize = args.base_optimize.strip()
    extra_flags = args.extra_flags.strip()
    mixed_optimize = " ".join(part for part in (base_optimize, extra_flags) if part)

    try:
        for obj in objects:
            (build_dir / obj).unlink(missing_ok=True)

        _run(
            [make, f"-j{args.jobs}", *_make_args(args, mixed_optimize), *objects],
            cwd=build_dir,
            env=env,
            log=log,
        )
        _run(
            [make, *_make_args(args, base_optimize), BUILD_EXE_NAME],
            cwd=build_dir,
            env=env,
            log=log,
        )
        variant_exe = variant_dir / EXE_REL.name
        shutil.copy2(build_exe, variant_exe)
        shutil.copy2(variant_exe, exe_path)

        for entry in selected:
            obj_path = build_dir / entry["object"]
            mixed_obj = mixed_object_dir / entry["object"]
            mixed_obj.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(obj_path, mixed_obj)
            entry["mixed_sha256"] = _sha256(obj_path)
            entry["mixed_object_size"] = obj_path.stat().st_size
            entry["mixed_object"] = str(mixed_obj)

        manifest = {
            "schema_version": "linx-spec-502-mixed-flags-v1",
            "generated_at_utc": _now_utc(),
            "spec_dir": str(args.spec_dir),
            "bench": BENCH,
            "build_dir": str(build_dir),
            "staged_exe": str(exe_path),
            "build_exe": str(build_exe),
            "variant_exe": str(variant_exe),
            "default_staged_exe_backup": str(backup_staged_exe),
            "default_build_exe_backup": str(backup_build_exe),
            "base_optimize": base_optimize,
            "extra_flags": extra_flags,
            "mixed_optimize": mixed_optimize,
            "mode": args.mode,
            "jobs": args.jobs,
            "selected_objects": selected,
            "baseline_staged_exe_sha256": _sha256(backup_staged_exe),
            "variant_exe_sha256": _sha256(variant_exe),
            "variant_left_staged": True,
            "build_objects_restored": False,
            "log": str(log),
        }
    finally:
        for backup, dest in restore_paths:
            if backup.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, dest)

    manifest["build_objects_restored"] = True
    manifest["build_exe_restored"] = True
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"manifest={manifest_path}")
    print(f"variant_exe={variant_exe}")
    print(f"staged_exe={exe_path}")
    print(f"restore_with={Path(__file__).resolve()} restore --out-dir {out_dir}")


def _restore(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir).resolve()
    manifest_path = out_dir / "mixed_flags_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"error: missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    staged_exe = Path(manifest["staged_exe"])
    build_exe = Path(manifest["build_exe"])
    backup_staged = Path(manifest["default_staged_exe_backup"])
    backup_build = Path(manifest["default_build_exe_backup"])
    if not backup_staged.is_file():
        raise SystemExit(f"error: missing staged exe backup: {backup_staged}")
    if not backup_build.is_file():
        raise SystemExit(f"error: missing build exe backup: {backup_build}")

    shutil.copy2(backup_staged, staged_exe)
    shutil.copy2(backup_build, build_exe)
    restore_manifest = {
        "schema_version": "linx-spec-502-mixed-flags-restore-v1",
        "generated_at_utc": _now_utc(),
        "source_manifest": str(manifest_path),
        "restored_staged_exe": str(staged_exe),
        "restored_build_exe": str(build_exe),
        "restored_staged_exe_sha256": _sha256(staged_exe),
        "expected_default_staged_exe_sha256": manifest["baseline_staged_exe_sha256"],
        "restored_matches_baseline": _sha256(staged_exe) == manifest["baseline_staged_exe_sha256"],
    }
    restore_path = out_dir / "restore_manifest.json"
    restore_path.write_text(json.dumps(restore_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not restore_manifest["restored_matches_baseline"]:
        raise SystemExit(f"error: restored staged exe digest mismatch; see {restore_path}")
    print(f"restore_manifest={restore_path}")


def _list(args: argparse.Namespace) -> None:
    spec_dir = Path(args.spec_dir).resolve()
    build_dir = spec_dir / BUILD_REL
    object_to_source = _object_map(build_dir)
    for obj, src in object_to_source.items():
        print(f"{obj}\t{src}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--spec-dir", default=str(DEFAULT_SPEC_DIR), help=f"SPEC root (default: {DEFAULT_SPEC_DIR})")

    list_p = sub.add_parser("list", parents=[common], help="List 502 source/object names.")
    list_p.set_defaults(func=_list)

    stage_p = sub.add_parser("stage", parents=[common], help="Stage a mixed-object 502 probe executable.")
    stage_p.add_argument("--out-dir", required=True, help="Generated artifact directory.")
    stage_p.add_argument("--objects", action="append", required=True, help="Object(s) or source(s) to compile with extra flags; repeatable or comma-separated.")
    stage_p.add_argument("--extra-flags", default=DEFAULT_EXTRA_FLAGS, help=f"Extra flags for selected objects (default: {DEFAULT_EXTRA_FLAGS})")
    stage_p.add_argument("--base-optimize", default=DEFAULT_BASE_OPTIMIZE, help=f"Baseline OPTIMIZE flags (default: {DEFAULT_BASE_OPTIMIZE})")
    stage_p.add_argument("--mode", default="phase-b", choices=("phase-a", "phase-b", "phase-c"))
    stage_p.add_argument("--jobs", type=int, default=max(os.cpu_count() or 1, 1))
    stage_p.add_argument("--force", action="store_true", help="Replace an existing manifest in --out-dir.")
    stage_p.set_defaults(func=_stage)

    restore_p = sub.add_parser("restore", help="Restore the default 502 executable after a staged probe.")
    restore_p.add_argument("--out-dir", required=True, help="Generated artifact directory used by stage.")
    restore_p.set_defaults(func=_restore)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
