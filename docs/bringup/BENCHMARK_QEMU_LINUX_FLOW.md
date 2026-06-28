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
- `workloads/generated/flow-linux-20260614/linux-userspace-entry-v3.json`
  records the current Linux hard break: `vmlinux` builds, the tiny initramfs
  userspace proof reaches QEMU-observed userspace PCs, and the clean BusyBox
  rootfs image still times out before shell command tokens.
- `docs/bringup/agent_runs/checklists/specint_qemu.md` records SPECint as a
  fast `test`/`train` gate first, with `505.mcf_r` isolated as VM stress rather
  than mixed into every cheap regression check.
- `docs/bringup/QEMU_SPECINT_PERFORMANCE_PLAN.md` records the current QEMU
  SPECint profile and the prioritized speedups for the Linx target.

Inference:

- Full benchmarks should not be the next default action from a dirty or
  partially repaired workspace. The efficient path is to stop at the first red
  prerequisite: ISA/catalog, compiler, QEMU, TSVC direct runtime, Linux
  userspace entry, libc hosted runtime, then full benchmark expansion.
- The current strict PR benchmark lane reaches the TSVC/QEMU stage. Treat
  TSVC direct runtime timeout or completion as the active PR hard break before
  spending time on Linux rootfs, libc runtime, or SPEC expansion.
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
| `specint-fast-gate` | integration | hard break | Run fast SPECint `test`/`train` suites before broad promotion work. |
| `full-benchmarks` | integration | hard break | Run CoreMark/Dhrystone and nightly SPECint test/train promotion only after upstream stages pass. |

## Commands

The `qemu-contract` stage seeds or refreshes the clean QEMU binary for runtime
stages. The flow runner and `run_gates.py` automatically prefer this binary
when its marker matches the current QEMU submodule SHA; otherwise they fall
back to the in-tree build path or any explicit `QEMU=...` override. When the
user has not set `QEMU`, the runner refreshes the resolved QEMU path before
each command so commands after `qemu-clean-build` use the newly built binary.

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

Run only the fast SPECint gate after Linux/libc prerequisites are green:

```bash
python3 tools/bringup/run_benchmark_linux_flow.py \
  --profile linux \
  --start-at specint-fast-gate \
  --stop-after specint-fast-gate \
  --report-out workloads/generated/flow-specint-fast/report.json
```

Run the current all-SPECint train diagnostic loop directly when the goal is to
classify every train workload rather than stop at PR smoke:

```bash
SPECINT_TRAIN_ALL_TIMEOUT=180 \
SPEC_GUEST_HEARTBEAT_SEC=0 \
SPEC_QEMU_HEARTBEAT_INTERVAL=50000000 \
SPEC_NO_PROGRESS_TIMEOUT=120 \
python3 tools/bringup/run_specint_fast_gate.py \
  --profile train \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --sysroot out/libc/musl/install/phase-b \
  --out-dir workloads/generated/specint-train-all-<date> \
  --append-extra norandmaps \
  --continue-on-fail
```

Use `LINX_TP_TRACE=1 LINX_TP_TRACE_LIMIT=<n>` only for focused TP/TLS
diagnosis. Use `LINX_TP_TRACE_SSR=1` or `LINX_TP_TRACE_READS=1` only after a
focused run identifies a TP handoff window; those switches are too noisy for
routine train-all profiling.

Use `LINX_QEMU_HEARTBEAT_REGS=1` only for focused register snapshots. The
normal train-all loop should rely on `LINX_HEARTBEAT` plus the runner summary
fields `heartbeat_running`, `heartbeat_site_progress`, `heartbeat_last_bpc`,
and `heartbeat_last_progress` to decide whether a timeout is deadlock or live
slow execution.

Use `LINX_QEMU_HEARTBEAT_CODE_BYTES=<n>` only for focused PC/BPC byte
snapshots after the summary identifies a narrow failure window. If a temporary
workload or library instrumentation changes a deterministic failure into a live
timeout, keep the original uninstrumented run as the canonical blocker and
record the instrumented run as perturbation evidence.

Use `LINX_SYSCALL_TRACE_DUMP_ARG=<0..5>` with
`LINX_SYSCALL_TRACE_NR=<nr>` for focused syscall copyout checks. Pair it with
`LINX_SYSCALL_TRACE_DUMP_BYTES=<n>` to cap the returned buffer dump; leave the
variable unset for normal train-all runs. This is the preferred next step when
the symptom is `errno`/fd/path corruption but `LINX_SYSCALL_RETURN` does not
show the reported errno.

Use `LINX_DEBUG_PC_WATCH=<pc>[,<pc>...] LINX_DEBUG_PC_WATCH_REGS=1` after a
fault, heartbeat, or symbolization pass identifies a narrow PC window. This
adds `LINX_PC_WATCH_REGS` full-register records without making the normal
train-all loop noisy. Reserve `LINX_DEBUG_PC_WATCH_EXIT=1` for short smoke
checks, not correctness runs.

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
- When `--report-out` is set, the flow runner writes per-command logs under
  `<report-dir>/logs/`. Use those logs, not terminal scrollback, as the
  handoff artifact for the first failed command.
- The tiny userspace proof can take slightly over 10 seconds on the current
  clean QEMU path, so the flow sets `TINY_USERSPACE_TIMEOUT=30` by default.

## Why This Is More Efficient

- It avoids expensive SPEC/rootfs/full benchmark runs when the cheaper QEMU or
  TSVC direct lane is already red, and it runs cheap SPECint `test`/`train`
  suites before any refrate-scale or broad promotion workload.
- It separates PR, Linux, and nightly profiles instead of using one monolithic
  strict run for every question.
- It makes the handoff boundary explicit for QEMU, compiler, libc, Linux, and
  ISA/docs agents, which reduces duplicate investigation across stale summaries.
