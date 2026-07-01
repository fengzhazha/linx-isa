#!/usr/bin/env python3
"""Audit downstream v0.57 PTO migration blockers.

Default mode validates the migration manifest and reports remaining stale
patterns without failing the command. Use --strict as the completion gate once
the downstream compiler, emulator, model, and benchmark updates are expected to
be finished.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MIGRATION = DEFAULT_ROOT / "isa/v0.57/state/downstream_migration.json"
DEFAULT_ENCODING = DEFAULT_ROOT / "isa/v0.57/state/pto_encoding.json"
DEFAULT_TILEOP_HEADER = DEFAULT_ROOT / "workloads/pto_kernels/include/common/pto_tileop.hpp"


@dataclass(frozen=True)
class Hit:
    target: str
    path: Path
    line: int
    pattern: str
    expected_delta: str


@dataclass(frozen=True)
class MissingRequirement:
    target: str
    pattern: str
    expected_delta: str
    paths: tuple[Path, ...]


def _as_list(value: Any, ctx: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{ctx} must be a list")
        return []
    return value


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _match_paths(root: Path, patterns: list[Any], ctx: str, errors: list[str]) -> list[Path]:
    paths: list[Path] = []
    for item in patterns:
        if not isinstance(item, str) or not item:
            errors.append(f"{ctx} contains invalid path glob {item!r}")
            continue
        matches = [Path(p) for p in glob.glob(str(root / item), recursive=True)]
        if not matches:
            errors.append(f"{ctx} glob matched no files: {item}")
        paths.extend(matches)
    return sorted(set(paths))


def _scan_file(path: Path, pattern: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if pattern in line:
            hits.append((lineno, line.rstrip()))
    return hits


def validate_manifest(data: dict[str, Any], encoding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("version") != "0.57.0":
        errors.append("downstream migration version must be 0.57.0")
    if data.get("isa") != "LinxISA":
        errors.append("downstream migration isa must be LinxISA")

    operations = _as_list(encoding.get("operations"), "pto_encoding.operations", errors)
    encoded_forms = {
        form
        for op in operations
        if isinstance(op, dict)
        for form in op.get("pto_ops", [])
        if isinstance(form, str)
    }
    required_forms = {
        form
        for form in _as_list(data.get("required_api_forms"), "required_api_forms", errors)
        if isinstance(form, str)
    }
    missing_forms = sorted(required_forms - encoded_forms)
    if missing_forms:
        errors.append(f"required API forms are not encoded: {', '.join(missing_forms)}")

    targets = _as_list(data.get("targets"), "targets", errors)
    for index, target in enumerate(targets):
        ctx = f"targets[{index}]"
        if not isinstance(target, dict):
            errors.append(f"{ctx} must be an object")
            continue
        if not isinstance(target.get("name"), str) or not target["name"]:
            errors.append(f"{ctx}.name must be a non-empty string")
        _as_list(target.get("required_delta"), f"{ctx}.required_delta", errors)
        _as_list(target.get("path_globs"), f"{ctx}.path_globs", errors)
        required_patterns = target.get("required_patterns", [])
        if required_patterns != []:
            required_patterns = _as_list(required_patterns, f"{ctx}.required_patterns", errors)
        for required_index, pattern in enumerate(required_patterns):
            pctx = f"{ctx}.required_patterns[{required_index}]"
            if not isinstance(pattern, dict):
                errors.append(f"{pctx} must be an object")
                continue
            if not isinstance(pattern.get("pattern"), str) or not pattern["pattern"]:
                errors.append(f"{pctx}.pattern must be a non-empty string")
            if not isinstance(pattern.get("expected_delta"), str) or not pattern["expected_delta"]:
                errors.append(f"{pctx}.expected_delta must be a non-empty string")
        patterns = _as_list(target.get("stale_patterns"), f"{ctx}.stale_patterns", errors)
        for pattern_index, pattern in enumerate(patterns):
            pctx = f"{ctx}.stale_patterns[{pattern_index}]"
            if not isinstance(pattern, dict):
                errors.append(f"{pctx} must be an object")
                continue
            if not isinstance(pattern.get("pattern"), str) or not pattern["pattern"]:
                errors.append(f"{pctx}.pattern must be a non-empty string")
            if not isinstance(pattern.get("expected_delta"), str) or not pattern["expected_delta"]:
                errors.append(f"{pctx}.expected_delta must be a non-empty string")
    return errors


def validate_tileop_constants(header: Path, encoding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not header.exists():
        return [f"TileOP header not found: {header}"]

    operations = encoding.get("operations")
    if not isinstance(operations, list):
        return ["pto_encoding.operations must be a list before TileOP constants can be checked"]

    expected: dict[str, int] = {}
    for op in operations:
        if not isinstance(op, dict) or op.get("opcode_space") != "TEPL.TileOpcode":
            continue
        mnemonics = op.get("mnemonics")
        enc_id = op.get("encoding_id")
        if (
            isinstance(mnemonics, list)
            and mnemonics
            and isinstance(mnemonics[0], str)
            and isinstance(enc_id, str)
        ):
            expected[mnemonics[0]] = int(enc_id, 16)

    text = header.read_text(encoding="utf-8")
    namespace_match = re.search(r"namespace\s+tepl\s*\{(?P<body>.*?)\n\}\s*//\s*namespace\s+tepl", text, re.S)
    if namespace_match is None:
        return [f"TileOP header has no namespace tepl constant block: {header}"]

    actual: dict[str, int] = {}
    for match in re.finditer(
        r"constexpr\s+unsigned\s+(?P<name>[A-Z0-9_]+)\s*=\s*(?P<value>0x[0-9a-fA-F]+|\d+)u\s*;",
        namespace_match.group("body"),
    ):
        actual[match.group("name")] = int(match.group("value"), 0)

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    mismatched = sorted(
        name for name in set(expected) & set(actual) if expected[name] != actual[name]
    )
    if missing:
        errors.append(f"TileOP TEPL constants missing: {', '.join(missing)}")
    if extra:
        errors.append(f"TileOP TEPL constants not in v0.57 map: {', '.join(extra)}")
    for name in mismatched:
        errors.append(
            f"TileOP TEPL constant {name} is 0x{actual[name]:02X}, "
            f"expected 0x{expected[name]:02X}"
        )
    return errors


def _has_tileop_wrapper(text: str, name: str) -> bool:
    return re.search(rf"\binline\s+void\s+{re.escape(name)}\s*\(", text) is not None


def validate_tileop_issue14_api(header: Path, encoding: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not header.exists():
        return [f"TileOP header not found: {header}"]

    coverage = encoding.get("supernpubench_issue_14_coverage")
    if not isinstance(coverage, dict):
        return []
    issue_ops = coverage.get("operations")
    if not isinstance(issue_ops, list):
        return []

    text = header.read_text(encoding="utf-8")
    required: set[str] = set()
    open_work: set[str] = set()
    for issue_op in issue_ops:
        if not isinstance(issue_op, dict):
            continue
        mnemonic = issue_op.get("mnemonic")
        if not isinstance(mnemonic, str) or not mnemonic:
            continue
        if issue_op.get("compiler_api_work_remaining") is False:
            required.add(mnemonic)
        elif issue_op.get("compiler_api_work_remaining") is True:
            open_work.add(mnemonic)

    if "TSTORE" in required:
        required.add("TSTORE_FP")

    for mnemonic in sorted(required):
        if not _has_tileop_wrapper(text, mnemonic):
            errors.append(
                f"TileOP issue #14 API marked covered but missing wrapper: {mnemonic}"
            )
    for mnemonic in sorted(open_work):
        if _has_tileop_wrapper(text, mnemonic):
            errors.append(
                f"TileOP issue #14 API still marked open but wrapper exists: {mnemonic}"
            )
    return errors


def scan(root: Path, data: dict[str, Any]) -> tuple[list[Hit], list[MissingRequirement], list[str]]:
    errors: list[str] = []
    hits: list[Hit] = []
    missing: list[MissingRequirement] = []
    for index, target in enumerate(data.get("targets", [])):
        if not isinstance(target, dict):
            continue
        name = target.get("name")
        target_name = name if isinstance(name, str) else f"target[{index}]"
        paths = _match_paths(
            root,
            target.get("path_globs", []),
            f"targets[{index}].path_globs",
            errors,
        )
        patterns = target.get("stale_patterns", [])
        if not isinstance(patterns, list):
            continue
        for pattern_obj in patterns:
            if not isinstance(pattern_obj, dict):
                continue
            pattern = pattern_obj.get("pattern")
            expected_delta = pattern_obj.get("expected_delta")
            if not isinstance(pattern, str) or not isinstance(expected_delta, str):
                continue
            for path in paths:
                for line, _text in _scan_file(path, pattern):
                    hits.append(
                        Hit(
                            target=target_name,
                            path=path.relative_to(root),
                            line=line,
                            pattern=pattern,
                            expected_delta=expected_delta,
                        )
                    )
        required_patterns = target.get("required_patterns", [])
        if not isinstance(required_patterns, list):
            continue
        for pattern_obj in required_patterns:
            if not isinstance(pattern_obj, dict):
                continue
            pattern = pattern_obj.get("pattern")
            expected_delta = pattern_obj.get("expected_delta")
            if not isinstance(pattern, str) or not isinstance(expected_delta, str):
                continue
            found = any(_scan_file(path, pattern) for path in paths)
            if not found:
                missing.append(
                    MissingRequirement(
                        target=target_name,
                        pattern=pattern,
                        expected_delta=expected_delta,
                        paths=tuple(path.relative_to(root) for path in paths),
                    )
                )
    return hits, missing, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--migration", type=Path, default=DEFAULT_MIGRATION)
    parser.add_argument("--encoding", type=Path, default=DEFAULT_ENCODING)
    parser.add_argument("--tileop-header", type=Path, default=DEFAULT_TILEOP_HEADER)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    root = args.root.resolve()
    migration_path = args.migration if args.migration.is_absolute() else root / args.migration
    encoding_path = args.encoding if args.encoding.is_absolute() else root / args.encoding
    tileop_header = args.tileop_header if args.tileop_header.is_absolute() else root / args.tileop_header

    migration = _load_json(migration_path)
    encoding = _load_json(encoding_path)
    if not isinstance(migration, dict):
        print("ERROR: migration manifest must be an object", file=sys.stderr)
        return 2
    if not isinstance(encoding, dict):
        print("ERROR: PTO encoding map must be an object", file=sys.stderr)
        return 2

    errors = validate_manifest(migration, encoding)
    errors.extend(validate_tileop_constants(tileop_header, encoding))
    errors.extend(validate_tileop_issue14_api(tileop_header, encoding))
    hits, missing, scan_errors = scan(root, migration)
    errors.extend(scan_errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if hits or missing:
        print(
            f"OPEN: {len(hits)} downstream v0.57 stale pattern hits, "
            f"{len(missing)} missing required patterns"
        )
        for hit in hits:
            print(
                f"{hit.path}:{hit.line}: {hit.target}: {hit.pattern!r} -> "
                f"{hit.expected_delta}"
            )
        for item in missing:
            paths = ", ".join(str(path) for path in item.paths)
            print(
                f"MISSING: {item.target}: {item.pattern!r} -> "
                f"{item.expected_delta} [{paths}]"
            )
        return 1 if args.strict else 0

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
