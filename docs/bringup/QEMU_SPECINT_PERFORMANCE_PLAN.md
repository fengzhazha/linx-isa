# QEMU SPECint Performance Plan

This note records the fast SPECint gate shape and the first QEMU profile taken
from that gate. Treat generated profiler output as evidence and this document as
the current optimization plan.

## Fast Gate Shape

Use `tools/bringup/run_specint_fast_gate.py` instead of launching full refrate
or the broad promotion set directly.

- `smoke`: `test-smoke` only, for quick local sanity.
- `pr`: `test-smoke` and `train-smoke`, both using `999.specrand_ir`.
- `nightly`: PR suites plus `test-cpu-stress`, `test-vm-stress`,
  `train-cpu-stress`, `train-vm-stress`, and train promotion breadth.

The gate uses initramfs by default to avoid 9p overhead while debugging QEMU
and Linux correctness. Use `--transports 9p,initramfs` only when transport
coverage is the point of the run.

## Initial Profile

Command shape:

```bash
SPECINT_TRAIN_CPU_STRESS_TIMEOUT=900 \
python3 tools/bringup/run_specint_fast_gate.py \
  --profile nightly \
  --suite train-cpu-stress \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --append-extra norandmaps \
  --guest-heartbeat-sec 0 \
  --heartbeat-sec 10 \
  --out-dir workloads/generated/specint-qemu-profile-20260627-train-cpu-stress/specint-train-cpu-stress
```

Sampling artifact:

- `workloads/generated/specint-qemu-profile-20260627-train-smoke/qemu-531.sample.txt`

The sampled process was `531.deepsjeng_r` on train input before the gate split
that workload out of `train-smoke`. A follow-up `531.deepsjeng_r` test-input
run also exceeded two minutes before guest-visible completion. The profile
shows the CPU thread spending most visible Linx-specific time under:

- `helper_linx_check_bstart_target`
- `linx_is_bstart_at_addr`
- `cpu_memory_rw_debug`
- `linx_mmu_translate`
- disabled debug/trace helpers, including `linx_dbg_check_mem`
- repeated `getenv`/`__findenv_locked` checks from hot helper paths

The main structural cost is indirect target validation reading guest text via
debug memory access, which then re-enters the Linx MMU walk. The main accidental
cost is disabled diagnostics still present in hot translated code.

## Implemented Low-Risk Fixes

- Cache the `LINX_CFI_TRACE` environment flag before the CFI helper hot path.
- Emit load/store debug watchpoint helpers only for TBs with
  `LINX_TB_FLAG_DBG_ACTIVE`.
- Remove temporary QEMU/kernel diagnostic logging before profiling.

Post-patch sample:

- `workloads/generated/specint-qemu-profile-20260627-train-cpu-stress-postpatch/qemu-531-postpatch.sample.txt`

Top-stack count changes from the initial sample to the post-patch sample:

| Frame | Before | After |
| --- | ---: | ---: |
| `__findenv_locked` | 1446 | 0 |
| `getenv` / `DYLD-STUB$$getenv` | 32 | 0 |
| `linx_dbg_check_mem` | 1157 | 0 |
| `helper_linx_dbg_check_load` | 180 | 0 |
| `helper_linx_dbg_check_store` | 66 | 0 |
| `helper_linx_check_bstart_target` | 249 | 130 |
| `linx_is_bstart_at_addr` | 369 | 182 |
| `cpu_memory_rw_debug` | 258 | 196 |
| `linx_mmu_translate` | 1347 | 933 |
| `address_space_translate_internal` | 2310 | 1567 |

The remaining QEMU-specific target is BSTART validation: indirect control-flow
checks still fetch guest text through `cpu_memory_rw_debug`, which repeatedly
enters address-space translation and Linx MMU walking.

## Implemented Target-Read Fix

QEMU commit `7e1981adf5f` replaces the Linx trap and block-recovery
instruction-byte probes with target-MMU-aware text reads. This removes
`cpu_memory_rw_debug` from that recovery path, preserves Linx legacy-MMU fault
details for diagnostics, and keeps user fault/IRQ resume state anchored to a
real BSTART header.

Validation after rebuilding `emulator/qemu/build-linx/qemu-system-linx64`:

- `qemu-system-linx64 --version` reports
  `v10.2.0-943-g7e1981adf5f`.
- `python3 avs/qemu/run_tests.py --all --timeout 20` passes.
- `./avs/qemu/check_system_strict.sh` passes.
- `boot_userspace_proof.py` reaches Linux userspace.
- `run_specint_fast_gate.py --profile smoke` passes on `999.specrand_ir`
  test input.

Post-fix 531 sample:

- `workloads/generated/specint-qemu-profile-20260627-test-cpu-stress-qemu7e/profile/qemu-531-test-qemu7e.sample.txt`

This sample was intentionally interrupted after profiling. It shows the
disabled diagnostic overhead is still gone, but `helper_linx_check_bstart_target`
continues to call `cpu_memory_rw_debug` from `helper.c`; the target-aware text
read fix did not yet move the hot CFI helper itself.

| Frame | Post-fix sample count |
| --- | ---: |
| `__findenv_locked` | 0 |
| `linx_dbg_check_mem` | 0 |
| `helper_linx_dbg_check_load` | 0 |
| `helper_linx_dbg_check_store` | 0 |
| `helper_linx_check_bstart_target` | 626 |
| `cpu_memory_rw_debug` | 1329 |
| `linx_mmu_translate` | 1157 |

## Implemented BSTART Cache-Hit Fix

QEMU commit `f80300d12c8` trusts positive BSTART cache hits on the hot CFI
path by default and moves that hit check before the call-fallthrough text
probe. `LINX_BSTART_CACHE_REVALIDATE=1` preserves the old revalidate-on-hit
behavior for self-modifying-code or mapping-churn debugging. Existing MMU
programming, TLB invalidation, CSTATE/ACR switches, and trap/ACRE transitions
reset the cache.

Validation after rebuilding `emulator/qemu/build-linx/qemu-system-linx64`:

- `qemu-system-linx64 --version` reports
  `v10.2.0-944-gf80300d12c8`.
- `python3 avs/qemu/run_tests.py --all --timeout 20` passes.
- `./avs/qemu/check_system_strict.sh` passes.
- `boot_userspace_proof.py` and `full_boot.py` reach Linux userspace.
- `run_specint_fast_gate.py --profile pr` passes on `999.specrand_ir`
  test and train input in `28.458s`.

Post-cache 531 sample:

- `workloads/generated/specint-qemu-profile-20260627-test-cpu-stress-bstart-cache/profile/qemu-531-test-bstart-cache.sample.txt`

The 531 stress run was intentionally interrupted after sampling. Compared with
the `7e1981adf5f` sample, visible helper/MMU/debug-memory frames dropped:

| Frame | Before cache hit trust | After cache hit trust |
| --- | ---: | ---: |
| `helper_linx_check_bstart_target` | 626 | 355 |
| `cpu_memory_rw_debug` | 1329 | 682 |
| `linx_mmu_translate` | 1157 | 524 |
| `address_space_translate_internal` | 552 | 296 |
| `linx_is_bstart_at_addr` | 733 | 340 |
| `__findenv_locked` | 0 | 0 |
| `linx_dbg_check_mem` | 0 | 0 |

## Implemented Helper Target-Read Fix

The next QEMU patch moves `helper_linx_check_bstart_target`,
`linx_is_bstart_at_addr`, and call-fallthrough validation away from
`cpu_memory_rw_debug`. The helper now uses a nonfaulting instruction-fetch
probe to copy RAM-backed guest text and preserves the previous demand-paging
behavior by deferring validation when executable text cannot be read.

Validation after rebuilding `emulator/qemu/build-linx/qemu-system-linx64`:

- `qemu-system-linx64 --version` reports
  `v10.2.0-945-g8f819f1df18`.
- `python3 avs/qemu/run_tests.py --all --timeout 20` passes.
- `./avs/qemu/check_system_strict.sh` passes.
- `boot_userspace_proof.py` and `full_boot.py` reach Linux userspace.
- `run_specint_fast_gate.py --profile pr` passes on `999.specrand_ir`
  test and train input.
- `SPECINT_TEST_CPU_STRESS_TIMEOUT=900 run_specint_fast_gate.py --profile
  nightly --suite test-cpu-stress` passes `531.deepsjeng_r` test input in
  `468.038s`; the benchmark exits 0, emits `LINX_SPEC_PASS`, and the
  `test.out` FNV-1a hash matches `0x391c9299`.

Post-target-read 531 sample:

- `workloads/generated/specint-nightly-test-cpu-stress-20260627-target-read/profile/qemu-531-test-target-read.sample.txt`

Compared with the immediately preceding current-QEMU 531 sample, the helper
path no longer samples `cpu_memory_rw_debug`, and the Linx MMU walk nearly
disappears from the sampled CFI validation stack:

| Frame | Before target-read helper | After target-read helper |
| --- | ---: | ---: |
| `helper_linx_check_bstart_target` | 363 | 244 |
| `cpu_memory_rw_debug` | 704 | 0 |
| `linx_mmu_translate` | 585 | 5 |
| `address_space_translate_internal` | 360 | 3 |
| `linx_is_bstart_at_addr` | 350 | 198 |
| `probe_access_flags` | 0 | 140 |

## 2026-06-28 BPC Heartbeat And Train-All Triage

Current Linx QEMU adds an opt-in Linx heartbeat in the QEMU log. Set either
`LINX_HEARTBEAT_INTERVAL` or `LINX_QEMU_HEARTBEAT_INTERVAL` to a nonzero
instruction-count interval. When enabled, QEMU emits `LINX_HEARTBEAT` records
with host time, instruction count, count delta, PC, BPC, body TPC, branch
state, `progress=first|site-change|same-site`, `same_site`, stack/return
registers, TP, ring-1 ETEMP/ETEMP0 breadcrumbs, and selected argument
registers. A high or growing `same_site` value means the same `(pc, bpc, tpc)`
location is recurring at heartbeat boundaries; changing BPC/PC with increasing
count means the guest is still executing and should be treated as slow, not
deadlocked.

For focused register snapshots at heartbeat sites, also set
`LINX_HEARTBEAT_REGS=1` or `LINX_QEMU_HEARTBEAT_REGS=1`. This emits a
`LINX_HEARTBEAT_REGS` companion line with the full Linx GPR file. The SPEC
runner lifts heartbeat evidence into `heartbeat_running`,
`heartbeat_site_progress`, `heartbeat_last_bpc`, `heartbeat_last_progress`,
`heartbeat_last_same_site`, and recent-count/site deltas in both per-benchmark
and matrix summaries.

For focused code identification without enabling full fault or PC-watch traces,
set `LINX_HEARTBEAT_CODE_BYTES=<n>` or `LINX_QEMU_HEARTBEAT_CODE_BYTES=<n>`.
QEMU emits `LINX_HEARTBEAT_CODE` records with up to 32 bytes at both the current
PC and BPC. Use this only for short or coarse-interval diagnostics; it reads
guest memory at every heartbeat boundary.

The SPEC fast gate now has an explicit `train` profile, backed by a `train-all`
suite covering all current Linx SPECint rate benchmarks:

- `500.perlbench_r`
- `502.gcc_r`
- `505.mcf_r`
- `520.omnetpp_r`
- `523.xalancbmk_r`
- `525.x264_r`
- `531.deepsjeng_r`
- `541.leela_r`
- `557.xz_r`
- `999.specrand_ir`

Additional opt-in QEMU debug switches used during this pass:

- `LINX_CALL_TRACE_RING=1` records recent call/return/ACRE events in a bounded
  ring and dumps them after `LINX_FAULT_TRACE` reports a synchronous fault.
  Use `LINX_CALL_TRACE_RING_SIZE=<1..128>` to tune the retained window.
- `LINX_MEM_TRACE_ADDR=<addr>` instruments translated loads/stores and prints
  only accesses overlapping the requested address range. Narrow with
  `LINX_MEM_TRACE_SIZE`, `LINX_MEM_TRACE_ACCESS=loads|stores|all`,
  `LINX_MEM_TRACE_LIMIT`, `LINX_MEM_TRACE_PC_LO/HI`, and
  `LINX_MEM_TRACE_ACR=<0..15>`. Use `LINX_MEM_TRACE_CONTEXT=1` when the trace
  must show the current user/kernel address-space context; it appends
  `mmu_idx`, `ttbr0`, `ttbr1`, and `tcr` to each matching record. QEMU now
  emits the helper call only for translated accesses that overlap the watched
  range; set `LINX_MEM_TRACE_FAST=0` to restore the older helper-on-every-access
  path if the fast address guard itself is under suspicion.
- `LINX_SYSCALL_TRACE=1` logs Linx hosted syscall entry and ACRE return pairs
  with syscall number, BPC/TPC, arguments, return value, and cstate. Narrow
  with `LINX_SYSCALL_TRACE_NR`, `LINX_SYSCALL_TRACE_LIMIT`, and
  `LINX_SYSCALL_TRACE_PC_LO/HI`.
- `LINX_SYSCALL_TRACE_STRINGS=1` augments syscall tracing with separate
  `LINX_SYSCALL_ARGSTR` records for pathname arguments. Bound reads with
  `LINX_SYSCALL_TRACE_STRING_MAX=<1..255>` so path/fd failures can be
  diagnosed without enabling full memory traces.
- `LINX_SYSCALL_TRACE_DUMP_ARG=<0..5>` dumps one syscall argument buffer on
  `LINX_SYSCALL_RETURN` as `LINX_SYSCALL_ARGDUMP`. Bound the read with
  `LINX_SYSCALL_TRACE_DUMP_BYTES=<1..256>`; the default is 64 bytes when an
  argument is selected. This is the low-noise copyout check for stat, ioctl,
  and similar output-buffer paths.
- `LINX_SYSCALL_TRACE_REGS=1` prints a `LINX_SYSCALL_REGS` record for each
  traced syscall entry and return with the full Linx GPR file. This is useful
  when return-value clobbering, TLS state, or caller-save handling is suspect.
- `LINX_FAULT_TRACE_REGS=1` prints a `LINX_FAULT_REGS` record after
  `LINX_FAULT_TRACE` reports a synchronous trap, again with the full GPR file.
- `LINX_TRACE_REGS=1` enables both syscall and fault register records.
- `LINX_HEARTBEAT_REGS=1` or `LINX_QEMU_HEARTBEAT_REGS=1` prints
  `LINX_HEARTBEAT_REGS` companion records with all GPRs at heartbeat sites.
  Use this only for focused runs; the normal train-all loop keeps it disabled.
- `LINX_HEARTBEAT_CODE_BYTES=<n>` or `LINX_QEMU_HEARTBEAT_CODE_BYTES=<n>`
  prints `LINX_HEARTBEAT_CODE` companion records with code bytes at PC and BPC.
  This is useful when runtime mapping is ambiguous and guest `/proc/<pid>/maps`
  is unavailable.
- `LINX_DEBUG_PC_WATCH=<pc>[,<pc>...]` prints focused architectural state when
  translation reaches specific PCs. Add `LINX_DEBUG_PC_WATCH_REGS=1` to emit
  `LINX_PC_WATCH_REGS` full-GPR companion records; `LINX_TRACE_REGS=1` also
  enables the PC-watch register records. Use `LINX_DEBUG_PC_WATCH_EXIT=1` only
  for short smoke checks.
- `LINX_DEBUG_PC_WATCH_DUMP_CODE_BYTES=<n>` adds a `LINX_PC_WATCH_CODE`
  companion record with up to 32 bytes at the watched PC.
- `LINX_DEBUG_PC_WATCH_DUMP_REGS=<reg>[,<reg>...]` dumps guest words from
  several GPR/TP/TQ/UQ pointer sources in one PC-watch hit. It shares
  `LINX_DEBUG_PC_WATCH_DUMP_WORDS` and `LINX_DEBUG_PC_WATCH_DUMP_OFFSET` with
  the single-source `LINX_DEBUG_PC_WATCH_DUMP_REG` path, and is useful when
  allocator or list corruption needs before/after chunk state from multiple
  registers in the same multi-billion-instruction run.
- `LINX_DEBUG_PC_WATCH_PRINT=0` suppresses immediate `linx_pc_watch:` output
  after the selected PC/count/hit/GPR filters pass. Pair it with
  `LINX_DEBUG_PC_WATCH_RING=1` to record matching hits in a bounded ring and
  dump them only when `LINX_FAULT_TRACE` reports a synchronous fault. Tune the
  retained window with `LINX_DEBUG_PC_WATCH_RING_SIZE=<1..128>`. This is the
  preferred path when synchronous PC-watch printing perturbs a SPEC failure.
  Add `LINX_DEBUG_PC_WATCH_RING_MEM_REG=<gpr|tp|tqN|uqN|t#N|u#N>` and
  `LINX_DEBUG_PC_WATCH_RING_MEM_OFFSET=<bytes>` when each deferred ring entry
  must also snapshot a guest 64-bit word derived from a watched pointer.
- `LINX_TP_TRACE=1` records user-to-kernel TP handoff points for service
  requests, synchronous traps, IRQ entry, same-ACR trap/IRQ frame creation, and
  ACRE staging. Same-ACR frame records include the interrupted `x1` value saved
  into ETEMP. Use `LINX_TP_TRACE_LIMIT=<n>` on full SPEC runs.
- `LINX_TP_TRACE_SSR=1` adds TP/ETEMP/ETEMP0 SSR writes and swaps to
  `LINX_TP_TRACE`. `LINX_TP_TRACE_READS=1` adds reads. These are high-volume
  options for focused runs, not for train-all profiling.

Static build command. Rebuild the SPEC-profile C++ runtime overlay after every
phase-b musl sysroot refresh; the musl install step replaces the sysroot
library directory, so a plain SPEC build otherwise fails the C++ benchmarks
with missing `-lc++`, `-lc++abi`, and `-lunwind`.

```bash
MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh

./tools/build_linx_llvm_cpp_runtimes.sh \
  --profile spec \
  --mode phase-b

LINX_SPEC_FORCE_STATIC=1 \
bash tools/spec2017/build_int_rate_linx.sh \
  --mode phase-b \
  --force-static \
  --emit-manifest workloads/generated/specint-build-after-oldmalloc-20260628/build_manifest_final.json
```

Original 600s static train-all run command, superseded for the active loop by
the 300s run below:

```bash
SPECINT_TRAIN_ALL_TIMEOUT=600 \
LINX_SPEC_HEARTBEAT_SEC=30 \
LINX_SPEC_QEMU_HEARTBEAT_INTERVAL=1000000000 \
LINX_SPEC_NO_PROGRESS_TIMEOUT=180 \
python3 tools/bringup/run_specint_fast_gate.py \
  --profile train \
  --out-dir workloads/generated/specint-train-all-20260628-static \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --append-extra norandmaps \
  --guest-heartbeat-sec 0 \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 1000000000 \
  --no-progress-timeout 180 \
  --continue-on-fail
```

Earlier rerun after the Linx oldmalloc early-page-size fix and C++ runtime
overlay rebuild. This used the redesigned faster 300s train-all budget:

```bash
SPECINT_TRAIN_ALL_TIMEOUT=300 \
LINX_SPEC_HEARTBEAT_SEC=30 \
LINX_SPEC_QEMU_HEARTBEAT_INTERVAL=1000000000 \
LINX_SPEC_NO_PROGRESS_TIMEOUT=180 \
python3 tools/bringup/run_specint_fast_gate.py \
  --profile train \
  --out-dir workloads/generated/specint-train-all-20260628-after-oldmalloc \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --append-extra norandmaps \
  --guest-heartbeat-sec 0 \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 1000000000 \
  --no-progress-timeout 180 \
  --continue-on-fail
```

Diagnostic rerun after the heartbeat-code-byte QEMU extension,
heartbeat-register smoke, PC-watch register/code-byte smoke, the QEMU
nested-CALL header hardening, and focused memtrace context/ACR filtering. This
was the first 180s all-train heartbeat loop:

```bash
python3 tools/bringup/run_specint_fast_gate.py \
  --profile train \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --sysroot out/libc/musl/install/phase-b \
  --out-dir workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1 \
  --append-extra norandmaps \
  --guest-heartbeat-sec 0 \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 50000000 \
  --no-progress-timeout 120 \
  --continue-on-fail
```

Current raw-prlimit train-all loop. This rerun uses the same all-ten SPECint
train suite, initramfs transport, no guest heartbeat, and QEMU heartbeat every
50M guest instructions. The SPEC runner now treats `LINX_USER_TRAP` as terminal
failure evidence and records it as the primary class even when the parent init
process would otherwise keep polling until a timeout. The generated init wrapper
also installs the SPEC stack limit with a raw `prlimit64` syscall before falling
back to libc `setrlimit()`, which bypasses the current libc return-value bug.

```bash
LINX_QEMU_HEARTBEAT_CODE_BYTES=0 \
SPEC_GUEST_HEARTBEAT_SEC=0 \
SPEC_QEMU_HEARTBEAT_INTERVAL=50000000 \
SPEC_NO_PROGRESS_TIMEOUT=120 \
python3 tools/bringup/run_specint_fast_gate.py \
  --profile train \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --sysroot out/libc/musl/install/phase-b \
  --out-dir workloads/generated/specint-train-all-20260629-raw-prlimit-r1 \
  --append-extra norandmaps \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 50000000 \
  --guest-heartbeat-sec 0 \
  --no-progress-timeout 120 \
  --transports initramfs \
  --continue-on-fail
```

Artifacts:

- `workloads/generated/specint-build-after-oldmalloc-20260628/build_manifest_final.json`
- `out/cpp-runtime/musl-cxx17-spec/summary_phase-b.json`
- `avs/qemu/out/musl-static-oldmalloc-page-20260628/summary.json`
- `avs/qemu/out/musl-tp-preserve-20260628-r2/summary.json`
- `avs/qemu/out/musl-tp-preserve-debug-r2-20260628/summary.json`
- `workloads/generated/specint-cxx-after-oldmalloc-20260628/run/qemu_matrix_summary.json`
- `workloads/generated/specint-cxx-startup-fix-20260628/build_manifest.json`
- `workloads/generated/specint-cxx-stacklimit-20260628/qemu-focused/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-after-oldmalloc/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260628-after-oldmalloc/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-after-oldmalloc/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/run/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/run/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/profile/qemu-523-xalancbmk-r.sample.txt`
- `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/profile/qemu-531-deepsjeng-r.sample.txt`
- `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/profile/qemu-557-xz-r.sample.txt`
- `workloads/generated/specint-train-all-20260628-liveness-v2/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260628-liveness-v2/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-liveness-v2/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260628-nestedcall-fix-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260628-nestedcall-fix-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-nestedcall-fix-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260628-heartbeat-code-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260628-heartbeat-code-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-heartbeat-code-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260628-copyout-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260628-copyout-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-copyout-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260628-qemu-context-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260628-qemu-context-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-qemu-context-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260629-raw-prlimit-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260629-raw-prlimit-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260629-raw-prlimit-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-999-prlimit-trace-20260629-r1/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-999-raw-prlimit-20260629-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-502-raw-prlimit-20260629-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-heartbeat-regs-smoke-20260628/qemu_matrix_summary.json`
- `workloads/generated/specint-heartbeat-regs-smoke-20260628/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-pcwatch-regs-smoke-20260628-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-pcwatch-regs-smoke-20260628-r1/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-heartbeat-code-smoke-20260628-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-heartbeat-code-smoke-20260628-r1/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-505-final-faultregs-20260628-r1/initramfs/505_mcf_r/run_001/qemu.log`
- `workloads/generated/specint-505-nestedcall-fix-20260628-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-502-syscall-argstr-smoke-20260628/run/initramfs/502_gcc_r/run_001/qemu.log`
- `workloads/generated/specint-502-static-fulltrace-post-gtod-20260628/run/initramfs/502_gcc_r/run_001/qemu.log`
- `workloads/generated/specint-502-fstat-argdump-20260628-r2/502_gcc_r/run_001/qemu.log`
- `avs/qemu/out/musl-time-syscalls-20260628/summary.json`

Result: all ten train-input benchmarks build in the static phase-b gate.
`999.specrand_ir` passes by hash. The other nine train-input benchmarks are
classified by first failing symptom. The latest same-ACR `x1` frame run finished
in `911.065s`; no failed benchmark was marked `stalled`, and every failed run
has `heartbeat_running=true` plus `heartbeat_site_progress=true`, so the
failures below are correctness or throughput stops rather than a global QEMU
deadlock.

Important 2026-06-29 correction: Linx `prlimit64` succeeds, but the current
libc `setrlimit()` wrapper reports `errno=21` after that successful syscall.
The SPEC init wrapper now calls raw `prlimit64` first and logs
`LINX_SPEC_DBG stack-limit=268435456`, so finite-stack train runs are effective
again. Keep `LINX_SPEC_STACK_LIMIT_BYTES=unlimited` available for reproducing
legacy unlimited-stack mmap layout failures.

| Benchmark | Result | Evidence | Current classification |
| --- | --- | --- | --- |
| `500.perlbench_r` | user arithmetic range | `Range iterator outside integer range at lib/Math/BigInt.pm line 2675`; no panic/trap; last heartbeat count `3350000002`, BPC `0x155582976a` | dlookup Oops is closed; resume Perl BigInt scalar/range correctness |
| `502.gcc_r` | user trap | `addr=0x305910060a11b059`, user `tpc=0x15559baa04`, `bpc=0x15559ba9fc`, `orig_tpc=0x1556076d02`, `orig_bpc=0x1556076ce4`; last heartbeat count `5700000000`, BPC `0xffffffff803dde02` | stack limit is effective; continue with fault regs/code bytes around the new GCC user BPC path and preserve the brk/mmap allocator evidence |
| `505.mcf_r` | live timeout at 180s | last heartbeat count `40350000005`, BPC `0x155555c44a`, `progress=site-change`, `stalled=false` | train input is now throughput/live-progress under the diagnostic budget; the older user trap is historical unless it reproduces |
| `520.omnetpp_r` | user trap | null trap at `tpc=0xeaea2`, `bpc=0xeae90`; last heartbeat count `750000002`, BPC `0xffffffff800fcede` | C++ object/callback correctness path; use fault regs plus call trace around the section/config path |
| `523.xalancbmk_r` | user trap | `addr=0x3feffffff8`, user `tpc=0x1555a6306a`, `bpc=0x1555a6306a`; last heartbeat count `10350000005`, BPC `0xffffffff800fe0da` | reclassify from live-slow to correctness under effective finite stack; use fault regs/code bytes around the C++ user trap |
| `525.x264_r` | live timeout at 180s | last heartbeat count `20800000000`, BPC `0xffffffff800019bc`, `progress=site-change`, `stalled=false` | current owner is throughput/live-progress; the older panic is historical unless it reappears |
| `531.deepsjeng_r` | live timeout at 180s | last heartbeat count `30450000007`, BPC `0x155556764a`, `progress=site-change`, `stalled=false` | current train input is slow/live; profile against the earlier test-input pass profile |
| `541.leela_r` | user trap | `addr=0x3feffffff8`, user `tpc=0x1555623796`, `bpc=0x1555623796`; last heartbeat count `5950000004`, BPC `0xffffffff803dde02` | now grouped with the C++/stack-edge user traps rather than live-slow |
| `557.xz_r` | live timeout at 180s | last heartbeat count `30500000010`, BPC `0x155558d612`, `progress=same-site` but recent unique sites `4`, `stalled=false` | current train input is slow/live; profile before pursuing older bad-pointer evidence |
| `999.specrand_ir` | pass | `LINX_SPEC_PASS 999.specrand_ir`; FNV-1a `rand.11.out` hash `0x973dcfc2` matches; last heartbeat count `450000000`, BPC `0xffffffff803dde02` | smoke sentinel closed |

The shared-runtime diagnostic run in
`workloads/generated/specint-train-all-20260628-after-kstat/` currently fails
all ten benchmarks quickly, including `999.specrand_ir`. That route is useful
for loader/libc diagnosis but is not the current SPEC correctness gate. The
static phase-b route is the baseline for benchmark correctness while shared
startup and C++ runtime packaging are being repaired.

The SPEC loop now records bounded failure classes and heartbeat-liveness fields
in both `stage_b_summary.json` and `qemu_matrix_summary.json`. A focused
`LINX_QEMU_HEARTBEAT_REGS=1` sentinel run proves the full-register heartbeat
switch without changing behavior: `999.specrand_ir` still passes and the QEMU
log contains `LINX_HEARTBEAT_REGS`. A separate
`LINX_DEBUG_PC_WATCH_REGS=1` smoke proves focused watchpoints can now emit
`LINX_PC_WATCH_REGS` full-GPR records. The new
`LINX_QEMU_HEARTBEAT_CODE_BYTES=16` sentinel run also passes
`999.specrand_ir` and emits `LINX_HEARTBEAT_CODE` records with PC/BPC bytes.
The new `LINX_DEBUG_PC_WATCH_DUMP_REGS=sp,tp,a0` sentinel run passes
`999.specrand_ir` and emits three same-hit guest-word dumps, so allocator and
list traces can capture multiple pointer sources in one long run.

Proposed next fixes:

1. Keep the QEMU heartbeat disabled by default, but enable it on long train
   runs to distinguish live progress from deadlock. Use BPC/PC churn plus
   `progress` and `same_site` before increasing timeouts.
2. Profile `505.mcf_r`, `525.x264_r`, `531.deepsjeng_r`, and `557.xz_r` with
   heartbeat off or at a very coarse interval. These workloads are live but too
   slow in the 180s train-all diagnostic loop; the next QEMU speedups should
   focus on page-local BSTART decode caching, TB-friendly template/queue fast
   paths, and avoiding helper probes in hot branch-validation paths.
3. Continue `500.perlbench_r` from the Perl BigInt range failure, not from the
   now-closed dcache Oops. The same-ACR QEMU frame fix restores Linux's
   kernel-origin entry contract: live `x1=0`, current-bank ETEMP holds the
   interrupted `x1`, and the dentry-name memory remains valid across the
   compare loop.
4. Continue `502.gcc_r` from the allocator/VM overlap. Syscall 169 now
   returns `0`; `200.c` opens as fd 3; `newfstatat(3, "", stat,
   AT_EMPTY_PATH)` returns `0`; and the `LINX_SYSCALL_ARGDUMP` buffer at
   `stat=0x3ffffff758` decodes with `st_mode=0x81a4` at offset 16, a regular
   file. The remaining failure is a later oldmalloc trap: `brk` stalls at
   `0x1556273000`, anonymous `mmap` returns at the same address, and a rejected
   one-page kernel guard only moves the symptom to `memset(0x1556273000, 0,
   0x1800)`. The latest `LINX_DEBUG_PC_WATCH_DUMP_REGS` trace proves the
   overlap mechanism: oldmalloc trims and bins both `0x1556272ff0` and
   `0x1556273010`, creating overlapping free chunks at `0x1556276010` and
   `0x1556276030`; a later allocation returns payload `0x1556276020`, and
   normal GCC GGC writes corrupt the still-binned `0x1556276030` node before
   the final `unbin` trap. The next fix should separate normal anonymous mmap
   placement from brk-frontier heap-extension mmap. Either keep non-heap
   anonymous mappings away from `mm->brk` in the Linx kernel mmap policy, or
   add a Linx oldmalloc large-mmap hint outside the heap-extension window while
   preserving fallback heap mmap at `end` when brk growth is exhausted.
5. Continue deterministic userspace traps separately from throughput work:
   `502.gcc_r` traps at `0x305910060a11b059`, `520.omnetpp_r` traps on a null
   object/callback path, and `523.xalancbmk_r` / `541.leela_r` trap at the
   stack-edge address `0x3feffffff8`. Use `LINX_FAULT_TRACE_REGS=1`,
   `LINX_CALL_TRACE_RING=1`, and, when a specific PC is known,
   `LINX_DEBUG_PC_WATCH_REGS=1` plus symbolization before changing QEMU
   control-flow rules. Older 505 focused runs showed `fflush` receiving a bad
   stdio/open-file pointer, but the latest train run is live-slow; reproduce
   the trap before returning 505 to the correctness lane. A follow-up
   `LINX_DEBUG_PC_WATCH_DUMP_CODE_BYTES=16` run corrected an earlier
   symbolization mistake: runtime `0x155555c254` has bytes
   `4100a50c0e000140b908d65259301108`, which match file offset `0x6254` /
   `primal_net_simplex` at ELF `0x40007254`. The source block at ELF
   `0x40002714` is a legitimate `global_opt -> primal_net_simplex` call, so
   this site is not the `__ofl_add` corruption point.
6. Keep the older `525.x264_r` panic evidence as a regression guard, but do
   not treat it as the active owner unless it reproduces. The latest run
   reaches live execution and times out with BPC progress; profile it with the
   other live slow workloads first.
7. Keep `train-all` opt-in through `--profile train`; the PR gate should stay
   on cheap `999.specrand_ir` smoke while stress workloads run in isolated
   nightly or diagnostic lanes.

## 2026-06-29 500 Dcache Oops Triage

The raw-prlimit train-all gate temporarily regressed `500.perlbench_r` from the
intermediate Perl BigInt user-range stop back into a kernel Oops in
`__d_lookup_rcu`. The current QEMU same-ACR frame fix closes that Oops and moves
`500.perlbench_r` back to the BigInt blocker:

- Baseline focused rerun:
  `workloads/generated/specint-500-baseline-20260629-r1/stage_b_summary.json`.
  It reproduces `LINX_DIE msg=Oops` at `tpc=0xffffffff8013c3de`,
  `bpc=0xffffffff8013c3d4`, followed by `LINX_EXIT_INIT code=0xb`. Symbolizing
  `kernel/linux/build-linx-fixed/vmlinux` maps the trap to the byte-compare loop
  in `__d_lookup_rcu`.
- Low-noise PC-watch filter:
  `workloads/generated/specint-500-dlookup-pcwatch-match-a1-20260629-r1/`.
  This reproduces the kernel panic while capturing the active lookup against
  `a1=0xff60000004c02d88`; the compared bytes spell paths such as
  `sec-run.linx_emptystdin`, and heartbeat still reports site progress.
- Ring-only PC-watch:
  `workloads/generated/specint-500-pcwatch-ring-a1-20260629-r1/`.
  `LINX_DEBUG_PC_WATCH_PRINT=0` plus `LINX_DEBUG_PC_WATCH_RING=1` avoids the
  synchronous print perturbation and dumps the last 64 watched hits when
  `LINX_FAULT_TRACE` catches the data exception. The final ring entry before
  the Oops records `pc=0xffffffff8013c3de`, `x1=0x1`,
  `x2=0xff6000007dd40027`, `a0=0xff60000004c020c0`,
  `a1=0xff60000004c02d88`, and `traparg0=0x1`. This proves the fault is a bad
  live-register value reaching the compare loop, not a deadlocked QEMU.
- Ring memory snapshot:
  `workloads/generated/specint-500-pcwatch-ring-mem-a1-20260629-r1/` adds
  `LINX_DEBUG_PC_WATCH_RING_MEM_REG=a1` and
  `LINX_DEBUG_PC_WATCH_RING_MEM_OFFSET=0x20`. The final ring entries show
  `x1=0x1` while `mem_value=0xff60000004c02db8` remains valid at `[a1+0x20]`.
  This rules out the dentry name field as the corrupted state and points at
  live `x1` handling.
- Root cause:
  Linux `arch/linx/kernel/entry.S` expects same-ACR kernel-origin traps and
  IRQs to enter with live `x1=0` and the interrupted `x1` saved in the current
  bank's ETEMP. QEMU saved EBARG/block state but did not populate that same-ACR
  `x1` frame, so a same-ring event could clobber the VFS compare loop's live
  `x1`.
- Fix and evidence:
  QEMU now builds same-ACR exception/IRQ frames before vectoring and TP trace
  emits `sync_same_acr_frame` / `irq_same_acr_frame` records when enabled. The
  focused rerun
  `workloads/generated/specint-500-after-same-acr-x1-20260629-r1/` has no
  kernel panic and reaches `Range iterator outside integer range at
  lib/Math/BigInt.pm line 2675`; the full train-all rerun
  `workloads/generated/specint-train-all-20260629-same-acr-x1-r1/` shows the
  same `user-arithmetic-range` class for `500.perlbench_r`.

Next solution path:

1. Keep the same-ACR `x1` entry contract covered by AVS and do not treat future
   500 BigInt failures as dentry corruption unless the Oops reproduces.
2. Resume the Perl BigInt `Range iterator outside integer range at
   lib/Math/BigInt.pm line 2675` investigation with a smaller Linx-native Perl
   scalar/range smoke or a non-perturbing QEMU watchpoint on the Perl range path.

## 2026-06-28 500 Fixup Triage

Focused `500.perlbench_r` runs separated the original loader-looking symptom
from the real kernel/runtime failures:

- `workloads/generated/specint-500-preexec-20260628/` proves the benchmark ELF
  exists in the initramfs and is readable before `execve`
  (`stat=0`, `open=6`, `read4=4`, ELF magic `0x7f454c46`).
- The first focused failure was a Linux Oops in `sys_fcntl` usercopy with BPC
  at `HL.BSTART.STD FALL<, fixup_label>`. The old Linux `fixup_exception`
  path only recognized legacy 128-bit block headers with the fixup attribute.
- `arch/linx/mm/extable.c` now recognizes the current v0.56 32-bit and
  48-bit `BSTART.{STD,SYS,FP} FALL` fixup encodings before falling back to the
  legacy header parser. Zero-offset FALL blocks are deliberately ignored so
  ordinary fallthrough blocks are not converted into recovery handlers.
- `workloads/generated/specint-500-fixup-20260628/` confirms that the first
  usercopy fixup blocker moved: the failure now reaches
  `kmem_cache_alloc_noprof` at `tpc=0xffffffff80102a96`,
  `bpc=0xffffffff80102a74`, with `a0=0`, `a1=0`, and
  `traparg0=0x24`.
- `workloads/generated/specint-500-kmalloc-centered-trace-20260628/` records
  the current QEMU `LINX_FAULT_TRACE` stop. The heartbeat count is still
  advancing until the Oops, so this is a deterministic kernel fault rather
  than a deadlock.
- `workloads/generated/specint-500-callring-20260628/` uses
  `LINX_CALL_TRACE_RING=1` to identify the null slab-cache dereference as
  `fcntl_setlk -> kmem_cache_alloc_noprof`, with `filelock_cache` still zero.
- The Linx curated `CONFIG_LINX_INTC` init path bypasses generic initcalls, so
  `filelock_init` was never reached. Calling `linx_filelock_init()` from the
  curated path initializes the lock-manager slab cache and moves 500 past the
  old kernel Oops.
- `workloads/generated/specint-500-after-filelock-20260628/` then showed a
  false relative-path `execve` failure. The initramfs already contained the
  benchmark ELF, and extracting the cpio proved the path existed; the robust
  runner fix is to exec `/spec-run/<benchmark>` in initramfs mode.
- `workloads/generated/specint-500-syscall-openat-ret-20260628/` proves
  `openat("perfect.pl")` returns fd `3` in the benchmark process. A following
  `LINX_SYSCALL_TRACE_NR=25` run proves `fcntl(3, F_SETFD, ...)` returns `0`;
  the old "Bad file descriptor" was caused by inheriting unusable fd `0`.
- The local SPEC runner now opens the generated `.linx_empty_stdin` file for
  no-stdin runs instead of inheriting initramfs fd `0`. With that fix,
  `workloads/generated/specint-500-stdin-empty-20260628/` reaches Perl BigInt
  user code and exits with `Range iterator outside integer range at
  lib/Math/BigInt.pm line 2675`.

Next 500-specific solution path:

1. Commit the filelock-init and runner stdin/absolute-exec fixes as SPEC flow
   prerequisites. The kernel Oops and false ENOENT/EBADF symptoms are now
   understood and should not be re-triaged as QEMU deadlocks.
2. Continue from the current BigInt user-code stop captured by
   `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/`. The next loop
   should compare the Linx static musl/compiler path against host SPEC behavior
   around `Math::BigInt.pm:2675` and the range iterator inputs before changing
   kernel/QEMU liveness policy.
3. Keep the v0.56 fixup parser as a prerequisite for all uaccess-heavy SPEC
   work; without it, normal faultable usercopy recovery is misclassified as an
   unhandled kernel page fault.

## Next Speedups

Current train-all live-progress evidence:

- `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/523_xalancbmk_r/run_001/qemu.log`
  last heartbeat: count `27850000004`, BPC `0xffffffff80090c62`,
  `progress=site-change`, recent unique sites `6`, and `stalled=false`.
- `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/525_x264_r/run_001/qemu.log`
  last heartbeat: count `24050000000`, BPC `0xffffffff803e8f46`,
  `progress=site-change`, recent unique sites `4`, and `stalled=false`.
- `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/541_leela_r/run_001/qemu.log`
  last heartbeat: count `11850000002`, BPC `0xffffffff80090e84`,
  `progress=site-change`, recent unique sites `8`, and `stalled=false`.
- `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/557_xz_r/run_001/qemu.log`
  no longer ends as a live timeout in the latest 180s loop. It reaches a
  bad-address user trap after heartbeat count `9050000000`; treat it as a
  correctness trap before spending more speedup budget on it.
- Short macOS `sample` captures during the same train-all run are stored under
  `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/profile/`
  for `523.xalancbmk_r`, `531.deepsjeng_r`, and `557.xz_r`.
- Earlier diagnostic samples in
  `workloads/generated/specint-train-all-20260628-debug-v2/profile/` included
  `helper_linx_scalar_read_reg`, `helper_linx_tq_push`,
  `helper_linx_heartbeat`, `helper_linx_tile_commit`,
  `helper_linx_template_step`, `helper_linx_uq_push`,
  `helper_linx_check_bstart_target`, and disabled trace initialization checks
  (`linx_cosim_init`, `linx_call_trace_init`, `linx_minst_trace_init`,
  `linx_commit_trace_init`).
- The latest liveness run did not collect fresh host samples. The current
  samples still show visible time in `helper_linx_scalar_read_reg`,
  `helper_linx_tq_push`, `helper_linx_tile_commit`,
  `helper_linx_template_step`, `helper_linx_check_bstart_target`, MMU
  lookup/probe paths, and `helper_linx_heartbeat`. Because this run
  deliberately enabled heartbeat, treat `helper_linx_heartbeat` as
  instrumentation cost.

Prioritized QEMU speedups:

1. Fast-path disabled trace helpers out of hot loops. The call-trace ring path
   now initializes once per event and returns immediately when both text trace
   and ring trace are disabled. `linx_trace_capture_active()` now avoids the
   generic active helpers on every writeback and reads cached
   commit/minst/cosim state after one-time init.
2. Add a page-local BSTART decode cache with explicit TB/text invalidation.
   Positive target caching reduces repeated hits, but cold or colliding targets
   still decode through the helper probe and BSTART byte classification.
3. Reduce helper traffic in the template/queue hot path. The current profile is
   dominated by `helper_linx_template_step`, `helper_linx_scalar_read_reg`,
   `helper_linx_tq_push`, `helper_linx_uq_push`, and tile commit/reset helpers;
   the next speed lane should inline simple scalar/queue cases into generated
   TCG or add a fused fast helper for the common scalar template sequence.
4. Keep heartbeat off, or at a very coarse interval, for profiler runs. Use it
   to classify deadlock vs live progress first, then rerun profiling with
   `LINX_QEMU_HEARTBEAT_INTERVAL=0` once the workload is known to be live.
5. Split correctness and instrumentation QEMU builds. The default benchmark
   binary should compile without always-on helper instrumentation; a separate
   diagnostics build can keep dense trace hooks and debug checks.
6. Keep 505 memory stress and `531` CPU stress out of cheap PR smoke. They
   should remain isolated as `test-vm-stress`, `train-vm-stress`,
   `test-cpu-stress`, and `train-cpu-stress` so ordinary regressions do not
   spend their budget on the largest allocation/MMU/control-flow workloads
   first.
7. Keep heartbeat and guest logging off for profiler runs. Use
   `--guest-heartbeat-sec 0` and a low or zero host heartbeat unless the guest
   is suspected of hanging.

## Validation Targets

- Rebuild `emulator/qemu/build-linx/qemu-system-linx64`.
- Run `run_specint_fast_gate.py --profile smoke` after each hot-path patch.
- For quick validation, run `train-smoke`; for performance comparisons, sample
  `train-cpu-stress` before and after the patch and compare the
  "Sort by top of stack" section for:
  - `__findenv_locked`
  - `linx_dbg_check_mem`
  - `helper_linx_dbg_check_load`
  - `helper_linx_dbg_check_store`
  - `cpu_memory_rw_debug`
  - `linx_mmu_translate`
