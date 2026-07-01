#!/usr/bin/env python3
"""Validate the LinxISA v0.57 PTO block-encoding map.

This checker is deliberately scoped to the v0.57 PTO map because that artifact
describes block-level PTO tile/data encodings, not the older compiled v0.56 ISA
catalog consumed by the existing generators.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_SPEC = Path("isa/v0.57/state/pto_encoding.json")

ALLOWED_CLASSES = {"TEPL", "CUBE", "TMA", "FIXP"}
EXPECTED_SPACE_BY_CLASS = {
    "TEPL": "TEPL.TileOpcode",
    "CUBE": "CUBE.Function",
    "TMA": "TMA.Function",
    "FIXP": "FIXP.Function",
}
EXPECTED_BLOCK_BY_CLASS = {
    "TEPL": {"BSTART.TEPL"},
    "CUBE": {"BSTART.CUBE"},
    "TMA": {"BSTART.TMA", "BSTART.TLOAD", "BSTART.TSTORE"},
    "FIXP": {"BSTART.FIXP"},
}
REQUIRED_FORMS = {
    "pto.tconcat",
    "pto.tconcatidx",
    "pto.tfillpad",
    "pto.tfillpad_expand",
    "pto.tfillpad_inplace",
}
FORBIDDEN_FORMS = set()
FORBIDDEN_MNEMONICS = set()
FORBIDDEN_PREFIXES = (
    "pto.comm.",
    "pto.record_event",
    "pto.wait_event",
    "pto.barrier",
    "pto.barrier_sync",
    "pto.sync.",
    "pto.tsync",
    "pto.talloc",
    "pto.tpush",
    "pto.tpop",
    "pto.tfree",
    "pto.tassign",
    "pto.subview",
    "pto.set_validshape",
    "pto.treshape",
    "pto.print",
)
REQUIRED_ISSUE14_FORMS = {
    "pto.trems",
    "pto.tinsert",
    "pto.tcolmax",
    "pto.tcolprod",
    "pto.tcolsum",
    "pto.trowprod",
    "pto.tmov",
    "pto.mgather",
    "pto.mscatter",
    "pto.tcvt",
    "pto.tdivs",
    "pto.texp",
    "pto.trecip",
    "pto.trowmax",
    "pto.trowsum",
    "pto.ttrans",
    "pto.tload",
    "pto.tstore",
    "pto.texpands",
    "pto.trowexpand",
    "pto.tci",
    "pto.tadd",
    "pto.tadds",
    "pto.tmax",
    "pto.tmaxs",
    "pto.tmins",
    "pto.tmul",
    "pto.tmuls",
    "pto.tsub",
}
REQUIRED_MERGED_FAMILIES = {
    "CUBE.Function.TGEMV": {
        "pto.tgemv",
        "pto.tgemv.acc",
        "pto.tgemv.bias",
        "pto.tgemv.mx",
        "pto.tgemv.mx.acc",
        "pto.tgemv.mx.bias",
    },
    "CUBE.Function.TMATMUL": {
        "pto.tmatmul",
        "pto.tmatmul.acc",
        "pto.tmatmul.bias",
        "pto.tmatmul.mx",
        "pto.tmatmul.mx.acc",
        "pto.tmatmul.mx.bias",
    },
    "TMA.Function.TPREFETCH": {
        "pto.tprefetch",
        "pto.tprefetch_async",
    },
    "TMA.Function.TSTORE": {
        "pto.tstore",
        "pto.tstore_fp",
    },
    "FIXP.Function.TEXTRACT": {
        "pto.textract",
        "pto.textract_fp",
    },
    "FIXP.Function.TINSERT": {
        "pto.tinsert",
        "pto.tinsert_fp",
    },
    "FIXP.Function.TMOV": {
        "pto.tmov",
        "pto.tmov.fp",
    },
    "FIXP.Function.TCONCAT": {
        "pto.tconcat",
        "pto.tconcatidx",
    },
    "FIXP.Function.TFILLPAD": {
        "pto.tfillpad",
        "pto.tfillpad_expand",
        "pto.tfillpad_inplace",
    },
}


def _as_list(value: Any, ctx: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{ctx} must be a list")
        return []
    return value


def _parse_hex_id(value: Any, ctx: str, errors: list[str]) -> int | None:
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{2,4}", value):
        errors.append(f"{ctx}.encoding_id must be a hex string such as 0x00")
        return None
    return int(value, 16)


def validate(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if data.get("version") != "0.57.0":
        errors.append("version must be 0.57.0")

    operations = _as_list(data.get("operations"), "operations", errors)
    all_forms: list[str] = []
    all_mnemonics: list[str] = []
    conflict_slots: dict[tuple[str, str], str] = {}
    key_slots: dict[str, str] = {}
    forms_by_opcode_key: dict[str, set[str]] = {}
    rows_by_class: Counter[str] = Counter()
    form_detail_seen: set[str] = set()

    for index, op in enumerate(operations):
        ctx = f"operations[{index}]"
        if not isinstance(op, dict):
            errors.append(f"{ctx} must be an object")
            continue

        enc_class = op.get("encoding_class")
        if enc_class not in ALLOWED_CLASSES:
            errors.append(f"{ctx}.encoding_class {enc_class!r} is not one of {sorted(ALLOWED_CLASSES)}")
            continue
        rows_by_class[enc_class] += 1

        opcode_space = op.get("opcode_space")
        expected_space = EXPECTED_SPACE_BY_CLASS[enc_class]
        if opcode_space != expected_space:
            errors.append(f"{ctx}.opcode_space must be {expected_space}, got {opcode_space!r}")

        block_start = op.get("block_start")
        if block_start not in EXPECTED_BLOCK_BY_CLASS[enc_class]:
            errors.append(
                f"{ctx}.block_start {block_start!r} is invalid for {enc_class}; "
                f"expected one of {sorted(EXPECTED_BLOCK_BY_CLASS[enc_class])}"
            )

        opcode_key = op.get("opcode_key")
        if not isinstance(opcode_key, str) or not opcode_key.startswith(f"{expected_space}."):
            errors.append(f"{ctx}.opcode_key must start with {expected_space}.")

        encoding_id = _parse_hex_id(op.get("encoding_id"), ctx, errors)
        if encoding_id is not None:
            if encoding_id > 0xFF:
                errors.append(f"{ctx}.encoding_id {op['encoding_id']} exceeds the v0.57 u8 local opcode field")
            slot = (str(opcode_space), op["encoding_id"])
            previous = conflict_slots.get(slot)
            if previous is not None:
                errors.append(f"{ctx} conflicts with {previous}: duplicate {slot[0]} id {slot[1]}")
            else:
                conflict_slots[slot] = ctx

        if isinstance(opcode_key, str):
            previous_key = key_slots.get(opcode_key)
            if previous_key is not None:
                errors.append(f"{ctx} conflicts with {previous_key}: duplicate opcode_key {opcode_key}")
            else:
                key_slots[opcode_key] = ctx
                forms_by_opcode_key[opcode_key] = set()

        pto_ops = _as_list(op.get("pto_ops"), f"{ctx}.pto_ops", errors)
        mnemonics = _as_list(op.get("mnemonics"), f"{ctx}.mnemonics", errors)
        if len(pto_ops) != len(mnemonics):
            errors.append(f"{ctx}.pto_ops and .mnemonics must have the same length")

        for form in pto_ops:
            if not isinstance(form, str) or not form.startswith("pto."):
                errors.append(f"{ctx}.pto_ops contains invalid PTO form {form!r}")
                continue
            all_forms.append(form)
            if isinstance(opcode_key, str):
                forms_by_opcode_key.setdefault(opcode_key, set()).add(form)
            if form in FORBIDDEN_FORMS or form.startswith(FORBIDDEN_PREFIXES):
                errors.append(f"{ctx} encodes forbidden non-tile/data PTO form {form}")

        for mnemonic in mnemonics:
            if not isinstance(mnemonic, str) or not mnemonic.strip():
                errors.append(f"{ctx}.mnemonics contains invalid mnemonic {mnemonic!r}")
            elif mnemonic in FORBIDDEN_MNEMONICS:
                errors.append(f"{ctx}.mnemonics encodes forbidden non-PTO mnemonic {mnemonic}")
            else:
                all_mnemonics.append(mnemonic)

        descriptor_sequence = _as_list(op.get("descriptor_sequence"), f"{ctx}.descriptor_sequence", errors)
        if not descriptor_sequence:
            errors.append(f"{ctx}.descriptor_sequence must not be empty")
        for desc in descriptor_sequence:
            if not isinstance(desc, str) or not desc.startswith(("BSTART.", "B.", "BSTOP")):
                errors.append(f"{ctx}.descriptor_sequence contains invalid descriptor {desc!r}")

        semantic_family = op.get("semantic_family")
        if not isinstance(semantic_family, str) or not semantic_family:
            errors.append(f"{ctx}.semantic_family must be a non-empty string")

        forms = _as_list(op.get("forms"), f"{ctx}.forms", errors)
        if len(forms) != len(pto_ops):
            errors.append(f"{ctx}.forms must describe every PTO form in pto_ops")
        seen_form_ids: set[str] = set()
        for form_index, form_obj in enumerate(forms):
            form_ctx = f"{ctx}.forms[{form_index}]"
            if not isinstance(form_obj, dict):
                errors.append(f"{form_ctx} must be an object")
                continue
            form_name = form_obj.get("pto")
            if form_name not in pto_ops:
                errors.append(f"{form_ctx}.pto {form_name!r} is not listed in {ctx}.pto_ops")
            if isinstance(form_name, str):
                form_detail_seen.add(form_name)
            form_id = form_obj.get("form_id")
            if not isinstance(form_id, str) or not re.fullmatch(r"0x[0-9a-fA-F]{2}", form_id):
                errors.append(f"{form_ctx}.form_id must be a two-digit hex string")
            elif form_id in seen_form_ids:
                errors.append(f"{form_ctx}.form_id {form_id} is duplicated within the row")
            else:
                seen_form_ids.add(form_id)
            selector = form_obj.get("selector")
            if not isinstance(selector, str) or not selector:
                errors.append(f"{form_ctx}.selector must be a non-empty string")
            summary = form_obj.get("semantic_summary")
            if not isinstance(summary, str) or not summary:
                errors.append(f"{form_ctx}.semantic_summary must be a non-empty string")

    duplicate_forms = sorted(k for k, v in Counter(all_forms).items() if v > 1)
    if duplicate_forms:
        errors.append(f"duplicate PTO forms across encoding rows: {', '.join(duplicate_forms)}")

    duplicate_mnemonics = sorted(k for k, v in Counter(all_mnemonics).items() if v > 1)
    if duplicate_mnemonics:
        errors.append(f"duplicate mnemonics across encoding rows: {', '.join(duplicate_mnemonics)}")

    forms_set = set(all_forms)
    missing_required = sorted(REQUIRED_FORMS - forms_set)
    if missing_required:
        errors.append(f"required real PTO instruction forms missing: {', '.join(missing_required)}")

    forbidden_present = sorted(FORBIDDEN_FORMS & forms_set)
    if forbidden_present:
        errors.append(f"forbidden PTO forms encoded: {', '.join(forbidden_present)}")
    forbidden_prefix_present = sorted(
        form
        for form in forms_set
        if any(form.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)
    )
    if forbidden_prefix_present:
        errors.append(
            "sync/communication/pipe/IR PTO forms must not be encoded: "
            + ", ".join(forbidden_prefix_present)
        )

    missing_issue14 = sorted(REQUIRED_ISSUE14_FORMS - forms_set)
    if missing_issue14:
        errors.append(f"SuperNPUBench issue #14 forms missing: {', '.join(missing_issue14)}")

    missing_form_details = sorted(forms_set - form_detail_seen)
    if missing_form_details:
        errors.append(f"forms missing detailed form entries: {', '.join(missing_form_details)}")

    for opcode_key, expected_forms in REQUIRED_MERGED_FAMILIES.items():
        actual_forms = forms_by_opcode_key.get(opcode_key)
        if actual_forms != expected_forms:
            missing = sorted(expected_forms - (actual_forms or set()))
            extra = sorted((actual_forms or set()) - expected_forms)
            detail = []
            if missing:
                detail.append(f"missing {', '.join(missing)}")
            if extra:
                detail.append(f"extra {', '.join(extra)}")
            if actual_forms is None:
                detail.append("missing opcode row")
            errors.append(f"{opcode_key} must be one merged encoding family ({'; '.join(detail)})")

    counts = data.get("encoding_counts")
    if not isinstance(counts, dict):
        errors.append("encoding_counts must be an object")
    else:
        expected_rows = len(operations)
        expected_forms = len(forms_set)
        expected_merged = sum(
            1 for op in operations if isinstance(op, dict) and len(op.get("pto_ops") or []) > 1
        )
        if counts.get("encoding_rows") != expected_rows:
            errors.append(f"encoding_counts.encoding_rows must be {expected_rows}")
        if counts.get("pto_instruction_forms_covered") != expected_forms:
            errors.append(f"encoding_counts.pto_instruction_forms_covered must be {expected_forms}")
        if counts.get("merged_encoding_rows") != expected_merged:
            errors.append(f"encoding_counts.merged_encoding_rows must be {expected_merged}")

    coverage = data.get("supernpubench_issue_14_coverage")
    if not isinstance(coverage, dict):
        errors.append("supernpubench_issue_14_coverage must be an object")
    else:
        issue_ops = _as_list(coverage.get("operations"), "supernpubench_issue_14_coverage.operations", errors)
        issue_forms = {op.get("pto") for op in issue_ops if isinstance(op, dict)}
        if issue_forms != REQUIRED_ISSUE14_FORMS:
            missing = sorted(REQUIRED_ISSUE14_FORMS - issue_forms)
            extra = sorted(str(x) for x in issue_forms - REQUIRED_ISSUE14_FORMS)
            if missing:
                errors.append(f"issue #14 coverage is missing: {', '.join(missing)}")
            if extra:
                errors.append(f"issue #14 coverage has extra forms: {', '.join(extra)}")
        if coverage.get("operation_count") != len(issue_ops):
            errors.append(f"issue #14 operation_count must be {len(issue_ops)}")
        for issue_op in issue_ops:
            if not isinstance(issue_op, dict):
                continue
            form = issue_op.get("pto")
            if form not in forms_set:
                errors.append(f"issue #14 form {form!r} is not covered by an encoding row")

    allocation = data.get("opcode_allocation")
    if not isinstance(allocation, dict):
        errors.append("opcode_allocation must be an object")
    else:
        allocated_by_space: defaultdict[str, list[str]] = defaultdict(list)
        for op in operations:
            if not isinstance(op, dict):
                continue
            space = op.get("opcode_space")
            enc_id = op.get("encoding_id")
            if isinstance(space, str) and isinstance(enc_id, str):
                allocated_by_space[space].append(enc_id)
        for space, ids in sorted(allocated_by_space.items()):
            entry = allocation.get(space)
            if not isinstance(entry, dict):
                errors.append(f"opcode_allocation missing {space}")
                continue
            allocated = entry.get("allocated")
            if allocated != len(set(ids)):
                errors.append(f"opcode_allocation[{space}].allocated must be {len(set(ids))}")
            if entry.get("id_width_bits") != 8:
                errors.append(f"opcode_allocation[{space}].id_width_bits must be 8")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    args = parser.parse_args(argv)

    errors = validate(args.spec)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
