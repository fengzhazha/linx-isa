#!/usr/bin/env python3
"""Run the QEMU/Linux benchmark bring-up hard-break flow."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qemu_build_paths import default_qemu_binary


VALID_PROFILES = {"pr", "linux", "nightly"}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def default_flow_path(root: Path) -> Path:
    return root / "docs" / "bringup" / "benchmark_qemu_linux_flow.json"


def load_flow(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"error: invalid flow JSON {path}: {exc}") from exc
    if data.get("schema_version") != 1:
        raise SystemExit(f"error: unsupported flow schema_version in {path}")
    stages = data.get("stages")
    if not isinstance(stages, list) or not stages:
        raise SystemExit(f"error: flow has no stages: {path}")
    seen: set[str] = set()
    for stage in stages:
        if not isinstance(stage, dict):
            raise SystemExit("error: each flow stage must be an object")
        stage_id = str(stage.get("id", "")).strip()
        if not stage_id:
            raise SystemExit("error: flow stage missing id")
        if stage_id in seen:
            raise SystemExit(f"error: duplicate flow stage id: {stage_id}")
        seen.add(stage_id)
        profiles = stage.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            raise SystemExit(f"error: stage {stage_id} missing profiles")
        bad_profiles = sorted(str(p) for p in profiles if p not in VALID_PROFILES)
        if bad_profiles:
            raise SystemExit(
                f"error: stage {stage_id} has invalid profiles: {', '.join(bad_profiles)}"
            )
        commands = stage.get("commands")
        if not isinstance(commands, list) or not commands:
            raise SystemExit(f"error: stage {stage_id} has no commands")
        seen_commands: set[str] = set()
        for command in commands:
            if not isinstance(command, dict):
                raise SystemExit(f"error: stage {stage_id} command must be an object")
            command_id = str(command.get("id", "")).strip()
            if not command_id:
                raise SystemExit(f"error: stage {stage_id} command missing id")
            if command_id in seen_commands:
                raise SystemExit(
                    f"error: duplicate command id in stage {stage_id}: {command_id}"
                )
            seen_commands.add(command_id)
            if not str(command.get("command", "")).strip():
                raise SystemExit(f"error: stage {stage_id}/{command_id} missing command")
    return data


def selected_stages(
    flow: dict[str, Any],
    *,
    profile: str,
    requested: list[str],
    start_at: str | None,
    stop_after: str | None,
) -> list[dict[str, Any]]:
    stages = [
        stage
        for stage in flow["stages"]
        if profile in {str(p) for p in stage.get("profiles", [])}
    ]
    if requested:
        wanted = set(requested)
        stages = [stage for stage in stages if stage["id"] in wanted]
        missing = sorted(wanted - {stage["id"] for stage in stages})
        if missing:
            raise SystemExit(
                "error: requested stage is not enabled for profile "
                f"{profile}: {', '.join(missing)}"
            )
    if start_at:
        ids = [stage["id"] for stage in stages]
        if start_at not in ids:
            raise SystemExit(f"error: --start-at stage not selected: {start_at}")
        stages = stages[ids.index(start_at):]
    if stop_after:
        ids = [stage["id"] for stage in stages]
        if stop_after not in ids:
            raise SystemExit(f"error: --stop-after stage not selected: {stop_after}")
        stages = stages[: ids.index(stop_after) + 1]
    return stages


def print_stage_list(stages: list[dict[str, Any]]) -> None:
    for idx, stage in enumerate(stages, start=1):
        hard = "hard-break" if stage.get("hard_break", True) else "non-blocking"
        print(f"{idx}. {stage['id']} [{stage.get('owner', 'unknown')}/{hard}]")
        for command in stage["commands"]:
            print(f"   - {command['id']}: {command['command']}")


def run_command(
    *,
    root: Path,
    stage_id: str,
    command: dict[str, Any],
    dry_run: bool,
    env: dict[str, str],
) -> dict[str, Any]:
    command_id = command["id"]
    rendered = str(command["command"])
    timeout = int(command.get("timeout_seconds", 0) or 0)
    print(f"-- {stage_id}/{command_id}")
    print(rendered)
    if dry_run:
        return {
            "id": command_id,
            "command": rendered,
            "status": "not_run",
            "returncode": 0,
            "timeout_seconds": timeout,
        }
    try:
        proc = subprocess.run(
            rendered,
            cwd=root,
            env=env,
            shell=True,
            executable="/bin/bash",
            timeout=timeout if timeout > 0 else None,
        )
        status = "pass" if proc.returncode == 0 else "fail"
        return {
            "id": command_id,
            "command": rendered,
            "status": status,
            "returncode": proc.returncode,
            "timeout_seconds": timeout,
        }
    except subprocess.TimeoutExpired:
        return {
            "id": command_id,
            "command": rendered,
            "status": "timeout",
            "returncode": 124,
            "timeout_seconds": timeout,
        }


def write_report(
    path: Path,
    *,
    flow: dict[str, Any],
    profile: str,
    dry_run: bool,
    stage_rows: list[dict[str, Any]],
) -> None:
    report = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "flow_id": flow.get("flow_id"),
        "profile": profile,
        "dry_run": dry_run,
        "ok": all(
            command["status"] in {"pass", "not_run"}
            for stage in stage_rows
            for command in stage["commands"]
        ),
        "stages": stage_rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"report: {path}")


def main(argv: list[str]) -> int:
    root = repo_root()
    ap = argparse.ArgumentParser(
        description="Run the fail-fast QEMU/Linux benchmark bring-up flow."
    )
    ap.add_argument("--flow", default=str(default_flow_path(root)))
    ap.add_argument("--profile", choices=sorted(VALID_PROFILES), default="pr")
    ap.add_argument("--stage", action="append", default=[], help="Run one stage id; may repeat")
    ap.add_argument("--start-at", default=None)
    ap.add_argument("--stop-after", default=None)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--continue-on-fail", action="store_true")
    ap.add_argument("--report-out", default="")
    args = ap.parse_args(argv)

    flow_path = Path(args.flow).resolve()
    flow = load_flow(flow_path)
    stages = selected_stages(
        flow,
        profile=args.profile,
        requested=args.stage,
        start_at=args.start_at,
        stop_after=args.stop_after,
    )
    if not stages:
        raise SystemExit(f"error: no stages selected for profile {args.profile}")
    if args.list:
        print_stage_list(stages)
        return 0

    env = os.environ.copy()
    env.setdefault("ROOT", str(root))
    env.setdefault("LINXISA_ROOT", str(root))
    env.setdefault("CLANG", str(root / "compiler" / "llvm" / "build-linxisa-clang" / "bin" / "clang"))
    env.setdefault("LLD", str(root / "compiler" / "llvm" / "build-linxisa-clang" / "bin" / "ld.lld"))
    env.setdefault("QEMU", str(default_qemu_binary(root)))

    stage_rows: list[dict[str, Any]] = []
    failed = False
    for stage in stages:
        stage_id = stage["id"]
        print()
        print(f"== {stage_id} ({stage.get('owner', 'unknown')})")
        if stage.get("why"):
            print(stage["why"])
        command_rows: list[dict[str, Any]] = []
        for command in stage["commands"]:
            row = run_command(
                root=root,
                stage_id=stage_id,
                command=command,
                dry_run=args.dry_run,
                env=env,
            )
            command_rows.append(row)
            if row["status"] not in {"pass", "not_run"}:
                failed = True
                break
        stage_rows.append(
            {
                "id": stage_id,
                "owner": stage.get("owner"),
                "hard_break": bool(stage.get("hard_break", True)),
                "commands": command_rows,
            }
        )
        if failed and stage.get("hard_break", True) and not args.continue_on_fail:
            print(f"hard-break: stopping at stage {stage_id}")
            break

    if args.report_out:
        write_report(
            Path(args.report_out).resolve(),
            flow=flow,
            profile=args.profile,
            dry_run=args.dry_run,
            stage_rows=stage_rows,
        )
    if failed:
        return 1
    print()
    print("ok: benchmark hard-break flow complete" if not args.dry_run else "ok: dry-run complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
