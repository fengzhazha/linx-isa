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
- `workloads/generated/busybox-rootfs-clean-rebuild-20260630/boot-r2/report.json`
  records a fresh local Linux rootfs proof: the clean rebuilt BusyBox rootfs
  boots from virtio-blk, reaches `/sbin/init`, runs shell commands, observes
  `linx-timer` IRQ progress `30 -> 35`, and powers off. The older
  `workloads/generated/busybox-rootfs-boot-20260630-r1/` `addr=0x10000004`
  PID1 trap used a stale rootfs image whose BusyBox binary still performed
  direct UART MMIO from user mode.
- `docs/bringup/agent_runs/checklists/specint_qemu.md` records SPECint as a
  fast `test`/`train` gate first, with `505.mcf_r` isolated as VM stress rather
  than mixed into every cheap regression check.
- `docs/bringup/QEMU_SPECINT_PERFORMANCE_PLAN.md` records the current QEMU
  SPECint profile and the prioritized speedups for the Linx target.
- `workloads/generated/specint-train-all-tlbfill-debug-qemu-20260630-r1/`
  is the current all-SPECint train diagnostic ledger. The run requested all ten
  SPECint train rows with initramfs, a 180s per-row timeout, QEMU BPC heartbeat
  every 1B guest instructions, and a `2G` stack limit. `999.specrand_ir` passes;
  `500.perlbench_r`, `505.mcf_r`, `520.omnetpp_r`, `523.xalancbmk_r`,
  `531.deepsjeng_r`, `541.leela_r`, and `557.xz_r` are heartbeat-backed
  `live-timeout` rows; `502.gcc_r` is a reopened Linux VM correctness lane at
  `addr=0x3f7fa8d010`; and `525.x264_r` hits an early VFS rootfs panic in
  initramfs mode. The focused
  `workloads/generated/specint-502-mprotect-tlbfill-20260630-r2/` trace shows
  the 502 store faults on a type0 legacy PTE after the `mprotect()` path returns
  to userspace, so the active 502 owner is Linux `mprotect()`/VMA/page-fault
  bring-up rather than QEMU stale-TLB policy.

Inference:

- Full benchmarks should not be the next default action from a dirty or
  partially repaired workspace. The efficient path is to stop at the first red
  prerequisite: ISA/catalog, compiler, QEMU, TSVC direct runtime, Linux
  userspace entry, libc hosted runtime, then full benchmark expansion.
- The current strict PR benchmark lane reaches the TSVC/QEMU stage, and the
  Linux BusyBox rootfs lane now has a fresh local pass. The next broad closure
  step is to refresh the canonical convergence/strict report and continue into
  libc hosted runtime plus SPEC correctness rather than reopening the stale
  BusyBox-rootfs image failure.
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
SPECINT_TRAIN_ALL_TIMEOUT=300 \
SPEC_GUEST_HEARTBEAT_SEC=0 \
SPEC_QEMU_HEARTBEAT_INTERVAL=1000000000 \
SPEC_NO_PROGRESS_TIMEOUT=180 \
python3 tools/bringup/run_specint_fast_gate.py \
  --profile train \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --sysroot out/libc/musl/install/phase-b \
  --out-dir workloads/generated/specint-train-all-<date> \
  --append-extra norandmaps \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 1000000000 \
  --guest-heartbeat-sec 0 \
  --no-progress-timeout 180 \
  --stack-limit 2G \
  --transports initramfs \
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

Use `LINX_TLB_FILL_TRACE=1` or `LINX_QEMU_TLB_FILL_TRACE=1` only for focused
page-walk windows. Narrow with `LINX_TLB_FILL_TRACE_VA=<addr>` or
`LINX_TLB_FILL_TRACE_VA_LO/HI`, plus `LINX_TLB_FILL_TRACE_COUNT_LO/HI`, before
running a SPEC row. Each record prints the requested VA, access kind, QEMU prot,
fault cause, PC/BPC/TPC, and the legacy leaf descriptor decision. This is the
preferred discriminator when a syscall such as `mprotect()` appears to succeed
but the next access still faults.

Use `LINX_SYSCALL_TRACE_DUMP_ARG=<0..5>` with
`LINX_SYSCALL_TRACE_NR=<nr>` for focused syscall copyout checks. Pair it with
`LINX_SYSCALL_TRACE_DUMP_BYTES=<n>` to cap the returned buffer dump; leave the
variable unset for normal train-all runs. This is the preferred next step when
the symptom is `errno`/fd/path corruption but `LINX_SYSCALL_RETURN` does not
show the reported errno.

Use `LINX_MEM_TRACE_CONTEXT=1` when a memory trace must prove whether two
stores come from the same guest address space. Pair it with
`LINX_MEM_TRACE_ACR=2` for focused userspace heap/list traces; leave both unset
for normal train-all runs because context printing belongs in narrow triage
windows.
For late SPEC faults, also set `LINX_MEM_TRACE_COUNT_LO=<insns>` and
`LINX_MEM_TRACE_COUNT_HI=<insns>` with the address/PC/ACR filters. Without a
count window, repeated stack-slot reuse can spend `LINX_MEM_TRACE_LIMIT` long
before the final producer.

Use `LINX_DEBUG_PC_WATCH=<pc>[,<pc>...] LINX_DEBUG_PC_WATCH_REGS=1` after a
fault, heartbeat, or symbolization pass identifies a narrow PC window. This
adds `LINX_PC_WATCH_REGS` full-register records without making the normal
train-all loop noisy. Reserve `LINX_DEBUG_PC_WATCH_EXIT=1` for short smoke
checks, not correctness runs.
For long SPEC loops, bound focused watchpoints with
`LINX_DEBUG_PC_WATCH_COUNT_LO=<insns>`, `LINX_DEBUG_PC_WATCH_COUNT_HI=<insns>`,
and `LINX_DEBUG_PC_WATCH_HIT_LIMIT=<n>` so a hot symbol does not flood the QEMU
log. The count window is an arming gate before PC matching, so late user faults
can be watched without paying a full reset-to-userspace PC-scan cost. A printed
watch record includes both the count-window hit count and the filtered
`printed=` count. The translator emits the host debug hook only for exact
`LINX_DEBUG_PC_WATCH` PCs; broad per-instruction hooks are reserved for co-sim
and work-grab debug modes. When a single PC window needs several frame or object slots,
use `LINX_DEBUG_PC_WATCH_DUMP_OFFSETS=<off>[,<off>...]` with
`LINX_DEBUG_PC_WATCH_DUMP_REGS=<reg>[,<reg>...]` so one run captures all needed
memory words.
Use `LINX_DEBUG_PC_WATCH_DUMP_WIDTH=1|2|4|8` only for focused structure-field
probes. The default remains 8-byte word dumps; narrower dumps are useful for
32-bit Perl SV flags, C++ object fields, and stack slots where 64-bit grouping
would hide the field boundary.
Use `LINX_DEBUG_PC_WATCH_DUMP_PTR_OFFSETS=<off>[,<off>...]` with
`LINX_DEBUG_PC_WATCH_DUMP_REGS=<reg>[,<reg>...]` when stack or object slots
hold guest pointers that need one-hop dereference in the same long run. This
keeps pointer provenance and pointee fields in one bounded PC-watch window; it
is too noisy for routine train-all loops.

When a fault-trace run is expected to dump a late PC-watch ring, pair
`LINX_FAULT_TRACE_PC_LO/HI` with `LINX_FAULT_TRACE_COUNT_LO/HI`. Early boot
faults and unrelated user faults otherwise consume `LINX_FAULT_TRACE_LIMIT`
before QEMU reaches the final SPEC window.

For user traps at `addr = sp - 8` or at the current stack bottom, run a bounded
stack-limit classifier before treating the failure as a C++ runtime, atomic, or
QEMU memory bug. Use `--stack-limit <bytes|512M|1G|2G|unlimited>` on
`run_int_rate_qemu.py`, `run_stage_qemu_matrix.py`, or
`run_specint_fast_gate.py`, and keep an explicit `--timeout`; if the failure
changes from `user-trap` to heartbeat-visible live progress, record it as stack
policy first. The current `541.leela_r` evidence follows this shape: `512M`
traps at `addr=0x3fdffffff8`, `1G` traps at `addr=0x3fbffffff8`, and `2G`
reaches a 240s live timeout with count `41550000002`, changing BPCs, and no
`LINX_USER_TRAP`.

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
