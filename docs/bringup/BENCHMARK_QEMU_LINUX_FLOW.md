# Benchmark QEMU/Linux Hard-Break Flow

This is the canonical execution order for moving from the current LinxISA
superproject state to full benchmark execution on QEMU with Linux. The
machine-readable source is `docs/bringup/benchmark_qemu_linux_flow.json`; the
runner is `tools/bringup/run_benchmark_linux_flow.py`.

## Current Analysis

Evidence:

- `docs/bringup/gates/qemu_isa_coverage_latest.md` was regenerated on
  2026-06-14 and records QEMU implementation coverage at `615/710` mapped
  spec mnemonics and `614/740` mapped legal forms.
- Recent TSVC evidence splits cleanly into compile coverage and QEMU runtime:
  compile coverage may be green while the PR benchmark lane still hard-breaks
  on TSVC/QEMU timeout or runtime completion.
- `docs/bringup/gates/logs/2026-05-20-r2-pin-post-compilerfix/pin/kernel_busybox_rootfs.log`
  records the full-OS BusyBox rootfs lane timing out without shell command
  progress under firmwareless QEMU.
- `docs/bringup/agent_runs/checklists/specint_qemu.md` records SPEC Stage-A as
  blocked behind firmwareless Linux userspace entry, not merely SPEC harness
  plumbing.

Inference:

- Full benchmarks should not be the next default action from a dirty or
  partially repaired workspace. The efficient path is to stop at the first red
  prerequisite: ISA/catalog, compiler, QEMU, TSVC direct runtime, Linux
  userspace entry, libc hosted runtime, then full benchmark expansion.
- The current hard-break priority is TSVC/QEMU for the PR benchmark lane, with
  BusyBox rootfs and libc runtime still real but downstream of that PR stop
  path.
- Markdown status pages are useful summaries, but several are stale relative to
  the current June 14 coverage snapshot and aggregate `latest.json` is older
  than some sidecar reports. Agents should use the JSON flow, command output,
  and fresh runner reports as the active source of truth for a new run.

## Stage Ladder

| Stage | Owner | Stop Rule | Purpose |
| --- | --- | --- | --- |
| `source-contract` | integration | hard break | Validate layout, canonical v0.56 catalog, and agent ownership map before build work. |
| `compiler-contract` | llvm | hard break | Prove active `clang` can build and cover the Linx64 AVS compile corpus. |
| `qemu-contract` | qemu | hard break | Prove strict QEMU AVS runtime and keep decode coverage visible. |
| `tsvc-qemu-hardbreak` | integration | hard break | Run compile-only TSVC floor, then batched QEMU TSVC before Linux rootfs or SPEC. |
| `linux-userspace-entry` | linux | hard break | Rebuild `vmlinux`, prove trivial initramfs userspace, then BusyBox rootfs. |
| `libc-hosted-runtime` | libc | hard break | Prove musl build/runtime and glibc runtime before hosted benchmarks. |
| `full-benchmarks` | integration | hard break | Run CoreMark/Dhrystone and SPEC Stage-A only after upstream stages pass. |

## Commands

Seed or refresh the clean QEMU binary for runtime stages. The flow runner and
`run_gates.py` automatically prefer this binary when its marker matches the
current QEMU submodule SHA; otherwise they fall back to the in-tree build path
or any explicit `QEMU=...` override.

```bash
bash tools/bringup/run_qemu_build_clean.sh \
  --qemu-root "$PWD/emulator/qemu" \
  --out-dir /tmp/linx-qemu-clean-build \
  --target qemu-system-linx64
```

List the selected PR stages:

```bash
python3 tools/bringup/run_benchmark_linux_flow.py --profile pr --list
```

Dry-run the PR hard-break path:

```bash
python3 tools/bringup/run_benchmark_linux_flow.py \
  --profile pr \
  --dry-run \
  --report-out workloads/generated/flow-pr-dry-run/report.json
```

Run the PR path and stop at the first real failure:

```bash
python3 tools/bringup/run_benchmark_linux_flow.py \
  --profile pr \
  --report-out workloads/generated/flow-pr/report.json
```

Run the Linux/full-OS expansion only after the PR path passes:

```bash
python3 tools/bringup/run_benchmark_linux_flow.py \
  --profile linux \
  --start-at linux-userspace-entry \
  --report-out workloads/generated/flow-linux/report.json
```

Run the promotion path only when the Linux path is green:

```bash
python3 tools/bringup/run_benchmark_linux_flow.py \
  --profile nightly \
  --report-out workloads/generated/flow-nightly/report.json
```

## Agentic Rules

- Work one stage at a time. Do not debug a downstream stage until every
  upstream hard-break stage is green in the same lane.
- Keep each agent inside its stage ownership unless the runner output proves a
  cross-stage failure. For example, a TSVC compiler crash belongs to `llvm`
  before it becomes a QEMU runtime problem.
- Publish a runner report for every run and attach the first failing command,
  return code, and log/artifact paths to the agent closeout.
- Put new generated benchmark artifacts under `workloads/generated/<run-id>/`.
  Do not create new `workloads/generated-*` sibling directories.
- Treat `skill-evolve` as a closeout decision. Update skills only when the
  failing stage teaches a reusable command, invariant, or triage order.

## Why This Is More Efficient

- It avoids expensive SPEC/rootfs/full benchmark runs when the cheaper QEMU or
  TSVC direct lane is already red.
- It separates PR, Linux, and nightly profiles instead of using one monolithic
  strict run for every question.
- It makes the handoff boundary explicit for QEMU, compiler, libc, Linux, and
  ISA/docs agents, which reduces duplicate investigation across stale summaries.
