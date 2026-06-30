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

For bounded 9p transport coverage, use `run_stage_qemu_matrix.py
--fail-9p-timeout` with train input. That mode treats a per-run 9p timeout as a
fast-gate failure and stops the current benchmark instead of continuing every
train invocation for full host-visible specdiff. The 2026-06-30 all-row 9p run
under `workloads/generated/specint-train-all-9p-failtimeout-20260630-r1/`
covers all ten supported SPECint rows and classifies every row as
heartbeat-backed `live-timeout`; this proves the current 9p suite state is
running, not deadlocked, but it is not a full correctness substitute for the
initramfs strict-hash sentinel or a long 9p specdiff run.

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

## 2026-06-29 BPC Heartbeat And Train-All Triage

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

For TLB-invalidation profiling, set `LINX_TLB_TRACE=1` or
`LINX_QEMU_TLB_TRACE=1`. QEMU emits bounded `LINX_TLB_TRACE` records with the
translated invalidation PC, BPC/TPC, ACR, control state, stack/return/TLS
registers, and selected arguments. `LINX_TLB_TRACE_LIMIT` defaults to 64 records
to avoid runaway logs; set it to `0` only for tightly filtered runs. Narrow with
open-ended or closed `LINX_TLB_TRACE_PC_LO/HI` and
`LINX_TLB_TRACE_COUNT_LO/HI` ranges. `LINX_TLB_TRACE_CODE_BYTES=<n>` dumps up to
32 bytes at the invalidation PC and BPC.

For page-walk/protection profiling, set `LINX_TLB_FILL_TRACE=1` or
`LINX_QEMU_TLB_FILL_TRACE=1`. QEMU emits bounded `LINX_TLB_FILL_TRACE` records
for TLB fill attempts, including requested VA, access kind, QEMU prot, fault
cause, PC/BPC/TPC, TCR/TTBR state, and the legacy page-table leaf descriptor
decision. `LINX_TLB_FILL_TRACE_LIMIT` defaults to 64 records. Narrow with
`LINX_TLB_FILL_TRACE_VA=<addr>` or `LINX_TLB_FILL_TRACE_VA_LO/HI`, plus
`LINX_TLB_FILL_TRACE_PC_LO/HI` and `LINX_TLB_FILL_TRACE_COUNT_LO/HI`, before
using it on SPEC rows. Matching `LINX_QEMU_TLB_FILL_TRACE_*` aliases are
accepted.

For kernel-space heartbeat timeouts, add `--symbolize-heartbeat` to the SPEC
runner, or set `LINX_SPEC_SYMBOLIZE_HEARTBEAT=1`. The runner symbolizes recent
kernel PC/BPC/RA heartbeat sites with `llvm-addr2line` against the active
`vmlinux` and records `heartbeat_kernel_symbols`,
`heartbeat_kernel_symbol_evidence`, and `heartbeat_kernel_panic_loop`. Timeout
rows whose recent heartbeat sites resolve into `panic.c` are reclassified as
`kernel-panic-loop-timeout` instead of generic `live-timeout`.

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

The direct train-all loop should keep `LINX_QEMU_HEARTBEAT_INTERVAL` enabled
and `SPEC_GUEST_HEARTBEAT_SEC=0`. QEMU heartbeat BPC/PC churn is the active
deadlock discriminator; guest wrapper output can remain quiet for minutes in
initramfs mode while SPEC is still executing.

For deadlock triage, set `LINX_HEARTBEAT_SAME_SITE_WARN=<n>` or
`LINX_QEMU_HEARTBEAT_SAME_SITE_WARN=<n>` alongside the heartbeat interval.
QEMU emits a one-shot `LINX_HEARTBEAT_STALL` line after the same
`(pc, bpc, tpc)` recurs for `n` heartbeat buckets. The record includes count,
delta, PC, BPC, TPC, ACR, CSTATE, repeat count, threshold, and
`status=same-site-running`. Treat it as a focused "probably spinning here"
marker, not as proof of a hard deadlock: the runner still reports
`heartbeat_site_progress=true` if later heartbeat buckets move to other BPCs.

The latest all-train static diagnostic run is
`workloads/generated/specint-train-all-latest-qemu-20260630-r1/`, using rebuilt
QEMU `v10.2.0-969-gf03477a0f56`. Its build manifest is
`workloads/generated/specint-build-all-static-byval-fix-20260630/phaseb_build_manifest.json`.
It uses the mallocng-default phase-b musl sysroot, the refreshed spec C++
runtime overlay, the Linx LLVM f64 extload fix, the indirect-call target-register
constraint, the `502.gcc_r` variadic-function-table workaround, the QEMU scalar
queue fast path, the QEMU heartbeat guard, the LLVM Blockify ABI call-arg fix,
and the LLVM by-value aggregate call fix in `compiler/llvm` commit
`870fb448edd6f`. It proves the current failed rows are not global QEMU
deadlocks: every failed row has QEMU heartbeat progress, increasing count/BPC
evidence, and `999.specrand_ir` still passes strict hash. That run splits the
work into five lanes:

- Closed 500 correctness stop: `500.perlbench_r` run_001 passes
  `perfect.b.3.out` by hash `0xc69c7085`; run_002 no longer traps at the old
  bad target `0x003f7fee56880000` and is now heartbeat-backed live-slow. The
  root cause was compiler-side: Blockify erased the shifted byte-count producer
  for ABI register `a2` before `Perl_repeatcpy`, corrupting Perl op pointers.
- Closed 502 byval correctness stop: `502.gcc_r` trapped at `addr=0x8` with
  `tpc=0x1555f26c0e`, `bpc=0x1555f26c02`, and `orig_tpc=0x1556075fe2`.
  With slide `0x1515555000`, the trap PC maps to `gsi_prev` in
  `tree-ssa-dse.c`, specifically the second list-link load after loading
  `[a0]`; the origin PC maps to the musl `mmap.c` return block. Focused runs
  under `workloads/generated/specint-502-gsiprev-pcwatch-20260629-r1/` and
  `workloads/generated/specint-502-gsiprev-ring-final-filtered-20260629-r1/`
  prove the final iterator slot itself is null: the final `LINX_PC_WATCH_RING`
  entry at `pc=0x1555f26c0e` has `a0=0x3ffffff750`, `mem_value=0x0`, and
  `tq0=0x0` immediately before the `addr=0x8` fault. The source signature
  `dse_optimize_stmt(..., gimple_stmt_iterator gsi)` takes the iterator by
  value, but that callee calls `gsi_remove(&gsi, true)`; the caller disassembly
  passes `sp+80` to `dse_optimize_stmt` and then reuses the same slot for
  `gsi_prev`. This is now closed by the Linx LLVM by-value aggregate lowering
  fix: by-value structs are copied to callee-owned temporaries before calls.
  The focused rebuild and rerun under
  `workloads/generated/specint-502-byval-fix-build-20260629/` and
  `workloads/generated/specint-502-byval-fix-train-20260629-r1/` crosses the
  former 35B-instruction trap window and reaches `live-timeout` at count
  `61000000006` with BPC `0x155598d706`, `progress=site-change`, and no
  `LINX_USER_TRAP`.
- Live-slow train rows: `500.perlbench_r` run_002, `502.gcc_r`, `505.mcf_r`,
  `531.deepsjeng_r`, and `557.xz_r` time out under diagnostic budgets with
  heartbeat site progress.
- Wrapper child-exit rows: `520.omnetpp_r`, `523.xalancbmk_r`, and
  `541.leela_r` emit `LINX_SPEC_FAIL child-exit`. The runner now appends the
  wrapper `LINX_SPEC_DBG wait ... status/code/sig` line to `spec-wrapper-fail`
  evidence, so the next rerun should identify whether each child exited
  nonzero or died by signal before treating these as C++ runtime or QEMU
  throughput failures.
- Kernel panic-loop row: `525.x264_r` does not reach `LINX_SPEC_START`; recent
  symbolized heartbeat sites resolve to `panic.c` and `udelay`, so the runner
  classifies it as `kernel-panic-loop-timeout` rather than throughput-only.
- Closed historical lanes: the earlier 502 bad RTL pointer path is closed by
  keeping indirect call targets out of ABI argument registers and by compiling
  502 with SPEC's existing `SPEC_GCC_VARIADIC_FUNCTIONS_MISMATCH_WORKAROUND`.
  The later 502 allocator/VM `mremap` end-page trap is closed by the Linx Linux
  mremap workaround and `avs/qemu/out/mremap-end-smoke-r3/summary.json`.
  Historical stack/startup traps for `520`, `523`, and `541` are not reproduced
  under the current `--stack-limit 2G` static train loop.

For `502.gcc_r`, the focused runs under
`workloads/generated/specint-502-icall-target-fix-20260629-r1` and
`workloads/generated/specint-502-icall-target-varfn-fix-20260629-r1` split the
root cause. The first run proves the indirect call target was no longer
allocated in `a0`, but the generated GCC table still called fixed-argument
`gen_*` functions through a variadic function-pointer type, conflicting with
Linx's stack-passed real-vararg policy. The 502-only SPEC workaround changes
that table to unprototyped calls, so `gen_movsi` receives operands in `a0/a1`
and the earlier `ix86_rtx_costs`/code-pointer trap is closed. The next stop was
the allocator/VM boundary: runtime `tpc=0x1556074e1a` mapped, with the static PIE
slide, to musl `realloc.c` at static `0x40b1fe1a`, immediately after the
`mremap.c` return body around static `0x40b2040a`. The trap wrote
`sbi a3, [a1, -4]` with `a1=0x3f7e729000`, faulting at `addr=0x3f7e728ffc`.
The Linx Linux mremap workaround still closes that old end-page producer:
`avs/qemu/out/mremap-end-smoke-r3/summary.json` passes the isolated end-page
store, and `workloads/generated/specint-train-all-mremap-fix-20260629-r1/`
classified 502 as heartbeat-backed live timeout at that point.

2026-06-30 correction: the current `502.gcc_r` allocator/VM lane is open again,
but the new evidence points away from QEMU stale-TLB behavior. In
`workloads/generated/specint-502-mprotect-tlbfill-20260630-r2/`, the final
mallocng metadata-page sequence enters `mprotect(0x3f7fa8d000, 0x1000,
PROT_READ|PROT_WRITE)` and the next store faults at `0x3f7fa8d010`. The new
`LINX_TLB_FILL_TRACE` record for that store reports `ok=0`, `access=store`,
`legacy_why=type0`, and `legacy_desc=0x0`; the companion `LINX_FAULT_TRACE`
reports `mem_va=0x3f7fa8d010`, `store_ok=0`, and
`legacy_store=1:0:type0`. Therefore the current owner is Linx Linux
`mprotect()`/VMA/page-fault bring-up: QEMU sees no writable or present legacy
PTE for the faulting data VA after the syscall path has returned to userspace.
The next kernel trace should log `do_mprotect_pkey()` VMA coverage and
`do_page_fault()` `find_vma()`/`access_error()` results for this VA before
changing QEMU TLB policy.

2026-06-30 VM-trace update: QEMU commit `883737038a7` plus the latest local
debug patch adds address-filtered fault tracing (`LINX_QEMU_FAULT_TRACE_ADDR*`)
and `LINX_QEMU_FAULT_TRACE_REGS`. The rebuilt Linx kernel adds boot-arg gated
VM fault UART tracing through `linx_vm_trace=1` and
`linx_vm_trace_addr=<va>`. Focused evidence under
`workloads/generated/specint-502-vmtrace-uart-20260630-r1/` proves the early
faults on `0x3f7fa8d008` have `LINX_VM_FAULT stage=good-vma` followed by
`stage=handled fault=0`, while the terminal store to `0x3f7fa8d010` has
`LINX_TLB_FILL_TRACE legacy_why=type0 legacy_desc=0x0`,
`LINX_FAULT_TRACE mem_va=0x3f7fa8d010`, and
`LINX_VM_FAULT stage=no-vma`. The active 502 owner is therefore Linux
VMA/mprotect/mapping lifetime, not QEMU liveness. The next fix should trace or
repair the kernel `mprotect()` VMA split/merge path around
`0x3f7fa8d000..0x3f7fa8efff` and then rerun this focused gate before touching
QEMU TLB policy.

2026-06-30 no-merge update: the focused mprotect trace and Linux fix close the
current 502 correctness stop. The new Linx-only kernel trace switch
`linx_mprotect_trace=1` logs `LINX_MPROTECT` before/after VMA neighborhoods,
with optional `linx_mprotect_trace_addr=<va>` and
`linx_mprotect_trace_limit=<n>`. Before the fix,
`workloads/generated/specint-502-mprotect-trace-20260630-r1/` showed the second
metadata-page `mprotect()` returning success while `prev`, `cur`, `next`, and
`target` all disappeared for `0x3f7fa8d010`; the next store then faulted as
`LINX_VM_FAULT stage=no-vma`. `mm/vma.c` now keeps Linx
`vma_modify()` operations out of `vma_merge_existing_range()`, matching the
existing Linx no-merge policy for mmap/brk/mremap until the maple-tree merge
path is repaired. After the fix,
`avs/qemu/out/musl-mprotect-adjacent-nomerge-20260630-r1/summary.json` passes
and the post-mprotect trace keeps both VMAs present. Focused `502.gcc_r` in
`workloads/generated/specint-502-mprotect-nomerge-20260630-r1/` moves from
`user-trap` to heartbeat-backed `live-timeout`, and the refreshed train-all
ledger `workloads/generated/specint-train-all-nomerge-qemu-20260630-r1/` keeps
`999.specrand_ir` passing strict hash `0x973dcfc2` while classifying `500`,
`502`, `505`, `520`, `523`, `531`, `541`, and `557` as live-slow and
`525.x264_r` as the remaining initramfs VFS-root panic. The next QEMU work is
therefore throughput profiling, not further 502 TLB correctness triage.

Additional opt-in QEMU debug switches used during this pass:

- `LINX_TLB_TRACE=1` records Linx TLB invalidation helpers with translated PC,
  BPC/TPC, ACR/control state, stack/return/TLS registers, and optional code
  bytes. Use `LINX_TLB_TRACE_COUNT_LO=<post-start-count>` when a host sample must
  exclude boot-time fixmap churn. Matching `LINX_QEMU_TLB_TRACE_*` aliases are
  accepted.
- `LINX_TLB_FILL_TRACE=1` records TLB fill/page-walk attempts with requested VA,
  access kind, QEMU prot, cause, TCR/TTBR state, and legacy leaf descriptor
  details. Use `LINX_TLB_FILL_TRACE_VA=<addr>` or `_VA_LO/_VA_HI` with count
  filters for long SPEC rows. Matching `LINX_QEMU_TLB_FILL_TRACE_*` aliases are
  accepted.
- `LINX_FAULT_TRACE=1` records synchronous fault handoff state, including
  source/destination ACR, faulting VA, report BPC, TPC, selected registers,
  instruction bytes, and fetch/store page-walk probes. Use
  `LINX_FAULT_TRACE_ADDR=<va>` or `_ADDR_LO/_ADDR_HI` to filter data faults by
  `pending_trap_arg0`; `LINX_FAULT_TRACE_VA*` is accepted as an alias for data
  VA filters. Matching `LINX_QEMU_FAULT_TRACE_*` aliases are accepted. Use
  `LINX_FAULT_TRACE_PC*`, `LINX_FAULT_TRACE_COUNT*`, and
  `LINX_FAULT_TRACE_TRAPNUM*` when a late SPEC run needs the quota to survive
  until the failing window.
- `LINX_CALL_TRACE_RING=1` records recent call/return/ACRE events in a bounded
  ring and dumps them after `LINX_FAULT_TRACE` reports a synchronous fault.
  Use `LINX_CALL_TRACE_RING_SIZE=<1..128>` to tune the retained window.
- `LINX_MEM_TRACE_ADDR=<addr>` instruments translated loads/stores and prints
  only accesses overlapping the requested address range. Narrow with
  `LINX_MEM_TRACE_SIZE`, `LINX_MEM_TRACE_ACCESS=loads|stores|all`,
  `LINX_MEM_TRACE_LIMIT`, `LINX_MEM_TRACE_PC_LO/HI`, and
  `LINX_MEM_TRACE_ACR=<0..15>`. Use `LINX_MEM_TRACE_COUNT_LO/HI` when a late
  SPEC window must retain the final producer instead of spending
  `LINX_MEM_TRACE_LIMIT` on earlier stack-slot reuse. Use
  `LINX_MEM_TRACE_CONTEXT=1` when the trace must show the current user/kernel
  address-space context; it appends `mmu_idx`, `ttbr0`, `ttbr1`, and `tcr` to
  each matching record. QEMU now emits the helper call only for translated
  accesses that overlap the watched range; set `LINX_MEM_TRACE_FAST=0` to restore
  the older helper-on-every-access path if the fast address guard itself is under
  suspicion.
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
- `LINX_FCMP_TRACE=1` or `LINX_FP_TRACE=1` records scalar FP compare helpers
  without enabling a full instruction trace. Narrow with
  `LINX_FCMP_TRACE_PC_LO/HI`, `LINX_FCMP_TRACE_COUNT_LO/HI`,
  `LINX_FCMP_TRACE_LIMIT`, and `LINX_FCMP_TRACE_OP=feq,flt,fge`; matching
  `LINX_FP_TRACE_*` aliases are accepted. Records include op, instruction
  count, PC, BPC, TPC, source type, raw operands, interpreted `f64`/`f32`
  values, result, and FCSR. Use this first for range/arithmetic failures where
  scalar compare operands or materialized FP constants are suspect.
- `LINX_DEBUG_PC_WATCH=<pc>[,<pc>...]` prints focused architectural state when
  translation reaches specific PCs. Add `LINX_DEBUG_PC_WATCH_REGS=1` to emit
  `LINX_PC_WATCH_REGS` full-GPR companion records; `LINX_TRACE_REGS=1` also
  enables the PC-watch register records. Use `LINX_DEBUG_PC_WATCH_EXIT=1` only
  for short smoke checks.
- `LINX_DEBUG_PC_WATCH_DUMP_CODE_BYTES=<n>` adds a `LINX_PC_WATCH_CODE`
  companion record with up to 32 bytes at the watched PC.
- `LINX_DEBUG_PC_WATCH_DUMP_REGS=<reg>[,<reg>...]` dumps guest words from
  several GPR/TP/TQ/UQ pointer sources in one PC-watch hit. It shares
  `LINX_DEBUG_PC_WATCH_DUMP_WORDS`, `LINX_DEBUG_PC_WATCH_DUMP_OFFSET`, and
  optional `LINX_DEBUG_PC_WATCH_DUMP_OFFSETS=<off>[,<off>...]` with the
  single-source `LINX_DEBUG_PC_WATCH_DUMP_REG` path. Use the offset list when
  allocator/list/frame corruption needs several slots from the same
  multi-billion-instruction run without rerunning the window.
- `LINX_DEBUG_PC_WATCH_DUMP_PTR_OFFSETS=<off>[,<off>...]` reads a 64-bit guest
  pointer from each selected source plus offset and dumps the pointee memory
  with the same word count and width controls. Use it for stack frames or SV/C++
  objects where the decisive state is one pointer hop away.
- `LINX_DEBUG_PC_WATCH_DUMP_WIDTH=1|2|4|8` changes the unit size for focused
  PC-watch memory dumps. The default is still 8-byte words with the old log
  shape; set width 4 for 32-bit flag fields, width 2 for packed halfwords, and
  width 1 for byte-level object or string fields.
- `LINX_DEBUG_PC_WATCH_COUNT_LO=<insns>` and
  `LINX_DEBUG_PC_WATCH_COUNT_HI=<insns>` arm PC matching only inside the chosen
  instruction-count window. Use this for late SPEC user faults after a
  fault-trace run has found the failing count; the PC-watch hit counter is then
  local to the armed window. The translator emits the host debug hook only for
  exact watched PCs, so PC-watch does not globally instrument reset-to-userspace
  execution.
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

## 2026-06-30 9p TLBI Trace

A focused 9p host sample for `999.specrand_ir` under
`workloads/generated/specint-profile-999-9p-current-20260630-r1/` showed visible
CPU-thread time in `helper_linx_tlb_iall`, `tlb_flush_by_mmuidx_async_work`, and
`tcg_flush_jmp_cache`. The new `LINX_TLB_TRACE` switch was added to determine
whether that cost is boot setup, 9p mount setup, or benchmark steady state.

Evidence:

- `workloads/generated/specint-tlbtrace-999-9p-20260630-r1/999_specrand_ir/run_001/qemu.log`
  records the first 80 invalidations. Apart from two reset-time low-address
  entries, all entries are before `LINX_SPEC_START` and symbolize through
  `kernel/linux/build-linx-fixed/System.map` to `get_pmd_virt_fixmap`,
  `get_pud_virt_fixmap`, and `get_p4d_virt_fixmap`.
- `workloads/generated/specint-tlbtrace-999-9p-postboot-20260630-r2/` reruns the
  same row with `LINX_TLB_TRACE_COUNT_LO=1000000000`. It emits zero
  `LINX_TLB_TRACE` records after the first heartbeat bucket while QEMU heartbeat
  reaches `count=5000000018`, `progress=site-change`, and
  `heartbeat_site_progress=true`.

Conclusion: the TLBI hot frames in whole-process samples are real, but for this
9p SPEC sentinel they are boot/fixmap biased, not the current post-start SPEC
bottleneck. Future host profiles must either start sampling after
`LINX_SPEC_START` or use QEMU count filters before optimizing the sampled top
frame.

Speedup candidates:

- QEMU: `tlb.iv` and the Linux packed-VA form of `tlb.iav` now use
  `tlb_flush_page()` plus page-scoped BSTART-cache invalidation instead of
  routing through full `tlb_flush()`. Preserve full flush for `tlb.iall` and
  keep `tlb.ia` conservative until QEMU models ASID-tagged TLB entries
  independently from TTBR/MMU-index state.
- QEMU: a future BSTART validation cache should move from direct-mapped target
  tags to page/generation-aware invalidation if self-modifying text or
  page-remap churn becomes visible in post-start profiles; current page-scoped
  TLBI only clears entries on the invalidated VA page.
- Linux: reduce redundant fixmap clear/set invalidations in
  `arch/linx/mm/init.c` during early page-table construction. This is a
  boot-time speed lane and should be validated with a boot/userspace proof before
  applying it to SPEC throughput claims.
- SPEC steady state: focus next on allocator/free-list heartbeat BPCs such as
  `kfree`/`__update_cpu_freelist_fast`, template/BSTART helper samples, tile
  block reset/set helpers, and 9p I/O transport overhead. Use initramfs
  `999.specrand_ir` as the cheap correctness sentinel; use 9p
  `999.specrand_ir` as the transport/profiling sentinel until a block-backed
  SPEC transport exists.

2026-06-30 page-scoped TLBI update: QEMU commit candidate
`target/linx/{helper.c,helper.h,translate.c}` splits the TLB maintenance
helpers. `tlb.iall` still performs a full local flush and full BSTART-cache
reset. `tlb.ia` now logs the ASID operand but remains a full flush because the
current QEMU TLB is not independently ASID-tagged. `tlb.iv` and Linux's packed
`tlb.iav` operand perform a one-page flush across all QEMU MMU indexes and only
clear BSTART-cache entries on the affected VA page. Validation evidence:
`avs/qemu/out/musl-mprotect-adjacent-tlbiv-pageflush-20260630-r1/summary.json`
passes and its log records `LINX_TLB_TRACE op=iv ... operand=...`;
`workloads/generated/specint-train-smoke-tlbiv-pageflush-20260630-r1/` passes
strict train `999.specrand_ir`; and focused
`workloads/generated/specint-502-tlbiv-pageflush-20260630-r1/` keeps
`502.gcc_r` in heartbeat-backed `live-timeout` with no `LINX_USER_TRAP`. This
closes the QEMU-side boot TLBI overshoot without changing the live-slow SPEC
steady-state owner list.

2026-06-30 scalar tile-commit guard update: a focused post-`LINX_SPEC_START`
host sample of train `531.deepsjeng_r` in
`workloads/generated/specint-profile-531-current-20260630-r1/profile/qemu-531-current.sample.txt`
showed `helper_linx_tile_commit` still visible in scalar SPEC blocks even
though no tile descriptor was pending. `target/linx/translate.c` now emits a
runtime guard around the helper and calls `linx_tile_commit` only when
`tile_iot_valid != 0`; this preserves descriptor state that may have been
decoded in an earlier TB while removing the no-op scalar helper call. The
follow-up sample
`workloads/generated/specint-profile-531-tilecommit-guard-20260630-r1/profile/qemu-531-tilecommit-guard.sample.txt`
has zero `helper_linx_tile_commit` occurrences by string-count comparison.
Validation evidence: `python3 avs/qemu/run_tests.py --all --timeout 20`,
`bash avs/qemu/check_system_strict.sh`, and
`workloads/generated/specint-train-smoke-tilecommit-guard-20260630-r1/` all
pass. The standalone `avs/qemu/run_tests.py --suite tile --timeout 120`
timeout reproduces after rebuilding the baseline without the guard, so that
row remains a pre-existing tile-suite duration/coverage lane rather than this
SPEC scalar fast-path proof.

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

Current train-all loop. This rerun uses the same all-ten SPECint train suite,
rebuilt QEMU `v10.2.0-970-g8dd1dcdbde2`, initramfs transport, no guest
heartbeat, QEMU heartbeat every 1B guest instructions, a `2G` stack limit, the
mallocng-default phase-b musl sysroot, and a refreshed spec C++ runtime overlay.
The SPEC runner treats
`LINX_USER_TRAP` as terminal failure evidence and records it as the primary
class even when the parent init process would otherwise keep polling until a
timeout. The generated init wrapper also installs the SPEC stack limit with a
raw `prlimit64` syscall before falling back to libc `setrlimit()`, which
bypasses the current libc return-value bug. The forced-static C++ startup
evidence from `workloads/generated/specint-520-cxx-startup-fix-20260629-r1`
still proves the old `_start`/constructor issue is closed; the latest all-train
run shows C++ rows now stop as child-exit wrapper rows with `sig=9`, not startup
traps.

```bash
python3 tools/spec2017/run_stage_qemu_matrix.py \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --stage b \
  --input-set train \
  --transports initramfs \
  --sysroot out/libc/musl/install/phase-b \
  --timeout 300 \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 1000000000 \
  --no-progress-timeout 180 \
  --guest-heartbeat-sec 0 \
  --append-extra norandmaps \
  --dump-prefix-bytes 256 \
  --stack-limit 2G \
  --symbolize-heartbeat \
  --out-dir workloads/generated/specint-train-all-latest-qemu-20260630-r1
```

The refreshed run reports `ok=false` after `2609.965s`: `999.specrand_ir`
passes strict hash `0x973dcfc2`; `500.perlbench_r` run_001 passes
`perfect.b.3.out` by hash and run_002 times out live; `502.gcc_r` is now a
heartbeat-backed live timeout rather than the old `LINX_USER_TRAP`; `505`,
`531`, and `557` are live timeouts; `520`, `523`, and `541` are wrapper
child-exit rows with `sig=9`; and `525.x264_r` is classified as
`kernel-panic-loop-timeout`. That split keeps the 502 compiler correctness lane
closed and routes remaining work to throughput profiling, wrapper/kill cause
capture, and a focused kernel panic-path probe.

Post-branch-fix all-train rerun. QEMU commit `085f20cc8bd` fixes the AVS
branch D0D2 failure where a predicated `FALL` edge skipped a marker-only
`DIRECT` trampoline but then entered the following `COND` header with
`cond/carg` reset. The QEMU rebuild passes `avs/qemu/run_tests.py --suite
branch --timeout 20`, `avs/qemu/run_tests.py --suite system --timeout 20`,
`avs/qemu/check_system_strict.sh`, and `avs/qemu/run_tests.py --all --timeout
20`.

The fresh all-SPECint train loop is
`workloads/generated/specint-train-all-post-branchfix-20260630-r1/`. It uses
the same all-ten train suite, rebuilt QEMU from the branch fix, initramfs
transport, `SPECINT_TRAIN_ALL_TIMEOUT=180`, QEMU heartbeat every 1B guest
instructions, `--no-progress-timeout 180`, `--stack-limit 2G`, and
`LINX_SPEC_SYMBOLIZE_HEARTBEAT=1`. The nested matrix command requested all ten
rows and completed in `1318.613s`; `999.specrand_ir` passed and the other rows
failed as follows:

| Bench | Class | Last BPC | Heartbeat | Current owner |
| --- | --- | --- | --- | --- |
| `500.perlbench_r` | `live-timeout` | `0xffffffff803d3a60` | `site-change`, count `107000000000` | Throughput: kernel maple-tree/mmap hot path after the old compiler bad-target failure is closed. |
| `502.gcc_r` | `user-trap` | `0x15557418b4` | `site-change`, count `6000000001` | Correctness: new trap at `addr=0x3f7fa8d010`, `tpc=0x1556088006`, `bpc=0x1556087ff4`; rerun with syscall/fault trace and symbolize the static-PIE slide before treating 502 as only slow. |
| `505.mcf_r` | `live-timeout` | `0x155555d0c6` | `site-change`, count `49000000005` | Throughput: user-space hot loop; profile post-`LINX_SPEC_START` before changing QEMU helpers. |
| `520.omnetpp_r` | `live-timeout` | `0xffffffff803d3ac0` | `site-change`, count `39000000004` | Throughput/kernel logging or VM path: no longer an immediate wrapper child-exit in this run. |
| `523.xalancbmk_r` | `live-timeout` | `0xffffffff8006c9b2` | `site-change`, count `42000000005` | Throughput/kernel logging path; check repeated printk/vsprintf/ring-buffer activity before blaming C++ runtime. |
| `525.x264_r` | `kernel-panic` | `0x0` | no running heartbeat | Transport/rootfs: initramfs panics with `VFS: Unable to mount root fs`; use 9p or add a block-backed SPEC root instead of growing the CPIO path. |
| `531.deepsjeng_r` | `live-timeout` | `0x15555630a8` | `site-change`, count `44000000009` | Throughput: user-space control-flow hot loop; keep as CPU stress sentinel. |
| `541.leela_r` | `live-timeout` | `0xffffffff803e0e5a` | `site-change`, count `41000000005` | Throughput/kernel string/memset path; investigate kernel log/memory churn after stack-limit traps remain closed. |
| `557.xz_r` | `live-timeout` | `0x155558d218` | `site-change`, count `36000000006` | Throughput: user-space compression loop; profile helper mix and timer/fault heartbeat sites. |
| `999.specrand_ir` | pass | `0x0` | finishes before heartbeat | Keep as the cheap strict-hash train sentinel. |

This run proves the all-row loop itself is not deadlocked: every timeout row
has QEMU BPC heartbeat progress. The next QEMU speed work should therefore use
post-start host sampling and the BPC ledger to avoid boot-biased samples. Start
with user-space rows (`505`, `531`, `557`) for target-helper/TB-cache cost,
then kernel-heavy rows (`500`, `520`, `523`, `541`) for maple-tree, printk, and
string/memset churn. Keep `502` separate as a correctness bug until the new
page-near trap is explained, and keep `525` on the transport/rootfs lane.

Heartbeat-stall train-all rerun. The latest all-ten initramfs loop using the
same branch-fix QEMU plus the heartbeat same-site warning switch is
`workloads/generated/specint-train-all-hbstall-qemu-20260630-r1/`:

```bash
LINX_QEMU_HEARTBEAT_SAME_SITE_WARN=4 \
SPECINT_TRAIN_ALL_TIMEOUT=180 \
python3 tools/bringup/run_specint_fast_gate.py \
  --profile train \
  --suite train-all \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --sysroot out/libc/musl/install/phase-b \
  --out-dir workloads/generated/specint-train-all-hbstall-qemu-20260630-r1 \
  --append-extra "norandmaps ignore_loglevel loglevel=8 linx_vm_trace=1 linx_vm_trace_addr=0x3f7fa8d000" \
  --guest-heartbeat-sec 0 \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 1000000000 \
  --no-progress-timeout 120 \
  --stack-limit 2G \
  --symbolize-heartbeat \
  --continue-on-fail
```

The aggregate finished in `1319.795s` with `ok=false`, but every current
SPECint C/C++ train row was attempted. `999.specrand_ir` passed strict train
hash `0x973dcfc2`. `502.gcc_r` reproduced the current VM correctness stop at
`addr=0x3f7fa8d010`; `525.x264_r` reproduced the initramfs VFS root panic.
The other failed rows were live-slow, not hard-deadlocked:

| Bench | Class | Last BPC | Heartbeat / stall evidence | Current owner |
| --- | --- | --- | --- | --- |
| `500.perlbench_r` | `live-timeout` | `0xffffffff803d3dfa` | site progress | Kernel-heavy throughput/profiling lane. |
| `502.gcc_r` | `user-trap` | `0x15557e88e8` | site progress before `LINX_USER_TRAP` | Linux VM/VMA/mprotect correctness lane, confirmed by focused VM trace. |
| `505.mcf_r` | `live-timeout` | `0x155555cbe2` | site progress | User-space throughput lane. |
| `520.omnetpp_r` | `live-timeout` | `0xffffffff803d407c` | site progress | Kernel-heavy throughput lane; no current wrapper child-exit in this loop. |
| `523.xalancbmk_r` | `live-timeout` | `0xffffffff8006af74` | site progress | Kernel-heavy throughput lane. |
| `525.x264_r` | `kernel-panic` | `0x0` | `LINX_PANIC ... VFS: Unable to mount root fs` | Initramfs/rootfs transport lane; use 9p or block-backed transport for train execution. |
| `531.deepsjeng_r` | `live-timeout` | `0x15555683b2` | site progress plus `LINX_HEARTBEAT_STALL status=same-site-running repeats=4 threshold=4` | CPU throughput lane; same-site warning works, but later site progress means not a proven deadlock. |
| `541.leela_r` | `live-timeout` | `0xffffffff803d1a44` | site progress | Kernel-heavy throughput lane. |
| `557.xz_r` | `live-timeout` | `0x155558d708` | site progress | User-space throughput lane. |
| `999.specrand_ir` | pass | n/a | strict hash pass before heartbeat needed | Keep as cheap correctness sentinel. |

Updated loop rule: use this heartbeat-stall configuration for bounded
all-train diagnostics and reserve `LINX_HEARTBEAT_REGS`,
`LINX_HEARTBEAT_CODE_BYTES`, `LINX_TLB_FILL_TRACE*`, and
`LINX_FAULT_TRACE*` for focused single-row runs. For speed profiling, disable
or coarsen heartbeat and start host sampling after `LINX_SPEC_START`, otherwise
kernel boot, printk/vsprintf, and early page-table setup dominate the sample.

Focused `525.x264_r` follow-up split that panic-path probe into transport work.
The initramfs train lane builds a 1.6 GiB CPIO and never reaches
`LINX_SPEC_START`; a PC-watch run on `panic()`/`vpanic()` with
`LINX_CALL_TRACE_RING=1` and `LINX_DEBUG_PC_WATCH_DUMP_CALL_RING=1` captures
the first panic string as `VFS: Unable to mount root fs on "%s" or %s`, with the
caller ring ending in `init/do_mounts.c`. A 4096 MiB rerun reproduces the same
VFS root panic, so this is not only a 2 GiB guest-memory limit. The SPEC 9p lane
now mounts successfully after the Linx usercopy and virtio feature-read fixes:
`workloads/generated/specint-525-9p-vmgetfeatures-wordfix-20260630-r1/` shows
the 9p mount-tag feature reaching the guest and both SPEC mounts returning zero.
The current 525 9p row reaches `LINX_SPEC_START` and classifies as
`live-timeout`, so its active owner is throughput/output validation on a
large-input transport, not the old `mount()` `-EFAULT` path. If 9p overhead stays
too high for full SPEC correctness, add a virtio-blk/ext2 SPEC transport instead
of duplicating large train inputs into initramfs.

Focused `500.perlbench_r` rerun after adding the scalar FP-compare trace in
QEMU commit `b5e90c7db5f`:

```bash
LINX_FCMP_TRACE=1 \
LINX_FCMP_TRACE_PC_LO=0x15556613ba \
LINX_FCMP_TRACE_PC_HI=0x15556614e0 \
LINX_FCMP_TRACE_OP=flt,fge \
LINX_FCMP_TRACE_LIMIT=128 \
LINX_SPEC_DUMP_PREFIX_BYTES=256 \
python3 tools/spec2017/run_stage_qemu_matrix.py \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --stage b \
  --input-set train \
  --transports initramfs \
  --sysroot out/libc/musl/install/phase-b \
  --timeout 180 \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 1000000000 \
  --no-progress-timeout 180 \
  --guest-heartbeat-sec 0 \
  --append-extra norandmaps \
  --dump-prefix-bytes 256 \
  --stack-limit 2G \
  --strict \
  --out-dir workloads/generated/specint-500-fcmp-trace-20260629-r2 \
  --bench 500.perlbench_r
```

Result: `workloads/generated/specint-500-fcmp-trace-20260629-r2` reproduces
the old `user-arithmetic-range` stop in `27.38s`. The QEMU log records
`LINX_FCMP_TRACE` lines for `S_outside_integer`: `fge.fd`/`flt.fd` compare
`1.0` against raw operands `0xdf000000`, `0x0`, and `0x5f800000`. Static
objdump confirms those operands come from `hl.lwu.pcr` immediately before
`.fd` compares, so 32-bit float bound constants are being interpreted as
64-bit doubles. That classified `500` as a Linx LLVM constant-pool/load-width
bug for double compare constants, not a QEMU FP helper issue. The follow-up
Linx LLVM fix adds a codegen regression and an AVS assembly gate, rebuilds all
SPECint binaries, and moves `500` to the live-timeout lane in
`workloads/generated/specint-train-all-f64-extload-fix-20260629-r1`.
The matrix summary now lifts this evidence into `fcmp_trace_seen`,
`fcmp_trace_count`, `fcmp_trace_last`, and bounded `fcmp_trace_samples` fields.

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
- `workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-all-20260629-stack2g-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260629-stack2g-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260629-stack2g-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-520-cxx-startup-fix-20260629-r1/build_manifest.json`
- `workloads/generated/specint-520-cxx-startup-fix-20260629-r1/ctor-watch/stage_b_summary.json`
- `workloads/generated/specint-520-cxx-startup-fix-20260629-r1/ctor-watch/520_omnetpp_r/run_001/qemu.log`
- `workloads/generated/specint-train-all-20260629-cxx-startup-fix-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260629-cxx-startup-fix-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260629-cxx-startup-fix-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-build-mallocng-cxx-refresh-20260629-r1/build_manifest.json`
- `workloads/generated/specint-train-all-20260629-mallocng-cxx-refresh-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-20260629-mallocng-cxx-refresh-r1/train-all/qemu_matrix_summary.json`
- `workloads/generated/specint-train-all-20260629-mallocng-cxx-refresh-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-500-fcmp-trace-20260629-r2/qemu_matrix_summary.json`
- `workloads/generated/specint-500-fcmp-trace-20260629-r2/initramfs/500_perlbench_r/run_001/qemu.log`
- `workloads/generated/specint-999-prlimit-trace-20260629-r1/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-999-raw-prlimit-20260629-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-502-raw-prlimit-20260629-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-heartbeat-regs-smoke-20260628/qemu_matrix_summary.json`
- `workloads/generated/specint-heartbeat-regs-smoke-20260628/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-pcwatch-regs-smoke-20260628-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-pcwatch-regs-smoke-20260628-r1/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-heartbeat-code-smoke-20260628-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-heartbeat-code-smoke-20260628-r1/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-pcwatch-dump-offsets-smoke-20260629-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-pcwatch-dump-offsets-smoke-20260629-r1/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-pcwatch-width-smoke-20260629-r2/qemu_matrix_summary.json`
- `workloads/generated/specint-pcwatch-width-smoke-20260629-r2/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-pcwatch-ptr-offset-smoke-20260629-r2/qemu_matrix_summary.json`
- `workloads/generated/specint-pcwatch-ptr-offset-smoke-20260629-r2/initramfs/999_specrand_ir/run_001/qemu.log`
- `workloads/generated/specint-500-ppflop-offsets-20260629-r1/initramfs/500_perlbench_r/run_001/qemu.log`
- `workloads/generated/specint-500-ppflop-sv-objects-20260629-r2/initramfs/500_perlbench_r/run_001/qemu.log`
- `workloads/generated/specint-500-ppflop-branch-ptrslots-20260629-r1/initramfs/500_perlbench_r/run_001/qemu.log`
- `workloads/generated/specint-500-ppflop-branch-countwin-20260629-r1/initramfs/500_perlbench_r/run_001/qemu.log`
- `workloads/generated/specint-505-final-faultregs-20260628-r1/initramfs/505_mcf_r/run_001/qemu.log`
- `workloads/generated/specint-505-nestedcall-fix-20260628-r1/qemu_matrix_summary.json`
- `workloads/generated/specint-502-syscall-argstr-smoke-20260628/run/initramfs/502_gcc_r/run_001/qemu.log`
- `workloads/generated/specint-502-static-fulltrace-post-gtod-20260628/run/initramfs/502_gcc_r/run_001/qemu.log`
- `workloads/generated/specint-502-fstat-argdump-20260628-r2/502_gcc_r/run_001/qemu.log`
- `workloads/generated/specint-502-mprotect-tlbfill-20260630-r2/qemu_matrix_summary.json`
- `workloads/generated/specint-502-mprotect-tlbfill-20260630-r2/initramfs/502_gcc_r/run_001/qemu.log`
- `workloads/generated/specint-train-all-tlbfill-debug-qemu-20260630-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-all-tlbfill-debug-qemu-20260630-r1/train-all/qemu_matrix_summary.json`
- `avs/qemu/out/musl-time-syscalls-20260628/summary.json`

Result: all ten train-input benchmarks build in the static phase-b gate.
`999.specrand_ir` passes by hash. The latest all-static diagnostic ledger is
`workloads/generated/specint-train-all-tlbfill-debug-qemu-20260630-r1/`.
It supersedes the older queue-inline/heartbeat-guard, after-callarg, byval, and
latest-qemu tables for current failure ownership while retaining those tables'
performance samples as historical profiling evidence. No timeout row is a
global QEMU deadlock: all timeout rows have `heartbeat_running=true` and
increasing count evidence, and all but `557.xz_r` have recent site changes.
`557.xz_r` is still running by count/BPC evidence, but its last recent window is
same-site and should use a finer heartbeat or PC-watch window before increasing
timeouts. `502.gcc_r` is the active correctness row, and `525.x264_r` is an
immediate initramfs VFS-root panic with no useful BPC heartbeat.

Focused 2026-06-29 502 update: after rebuilding `502.gcc_r` with the Linx LLVM
byval aggregate fix, `workloads/generated/specint-502-byval-fix-train-20260629-r1/`
reclassifies the former `gsi_prev addr=0x8` correctness stop as live-slow. The
run reaches count `61000000006` and BPC `0x155598d706` at the 420s timeout with
`heartbeat_running=true`, `heartbeat_site_progress=true`, and no user trap.

Important 2026-06-29 correction: Linx `prlimit64` succeeds, but the current
libc `setrlimit()` wrapper reports `errno=21` after that successful syscall.
The SPEC init wrapper now calls raw `prlimit64` first and logs
`LINX_SPEC_DBG stack-limit=268435456`, so finite-stack train runs are effective
again. The SPEC runners and fast gate now accept
`--stack-limit <bytes|512M|1G|2G|unlimited>` and record the active define in
JSON summaries. Keep `--stack-limit unlimited` available for reproducing legacy
unlimited-stack mmap layout failures.

| Benchmark | Result | Evidence | Current classification |
| --- | --- | --- | --- |
| `500.perlbench_r` | `live-timeout` | count `107000000000`, BPC `0xffffffff803d3a9c`, `progress=site-change`; recent kernel symbols are in `maple_tree.c` | Old bad branch target is closed. Current owner is live-slow throughput/VMA-maple-tree profiling, not global deadlock. |
| `502.gcc_r` | `user-trap` | all-train row traps at `addr=0x3f7fa8d010`, `tpc=0x1556088006`, `bpc=0x1556087ff4`; focused TLB-fill trace reports `legacy_why=type0`, `legacy_desc=0x0` for the store VA | Active correctness row. Owner is Linx Linux `mprotect()`/VMA/page-fault bring-up, not QEMU stale-TLB or compiler byval. |
| `505.mcf_r` | `live-timeout` | count `48000000005`, BPC `0x155555c482`, `progress=site-change` | Throughput/live-progress lane; reproduce older traps before reopening correctness. |
| `520.omnetpp_r` | `live-timeout` | count `40000000001`, BPC `0xffffffff803e2694`, `progress=site-change`; recent symbols include `string.c`/`memory.c` | Resource-sensitive C++ row is currently live-slow, not the older `sig=9` wrapper failure. Profile kernel memory/string hot paths under <=4 GiB. |
| `523.xalancbmk_r` | `live-timeout` | count `39000000005`, BPC `0xffffffff803e0e5a`, `progress=site-change`; recent symbols include `vsprintf.c` and `string.c` | Live-slow kernel formatting/string lane in this run; old wrapper-output failure is historical unless reproduced. |
| `525.x264_r` | `kernel-panic` | `LINX_PANIC caller=0xffffffff80001648 msg=VFS: Unable to mount root fs on "" or unknown-block(0,0)`; no useful BPC heartbeat | Initramfs packaging/rootfs-size panic sentinel. Use 9p or a disk/rootfs transport for benchmark execution after fixing the initramfs mount path. |
| `531.deepsjeng_r` | `live-timeout` | count `43000000001`, BPC `0x15555593e4`, `progress=site-change` | Throughput/live-progress lane; compare with the passing test-input profile. |
| `541.leela_r` | `live-timeout` | count `42000000001`, BPC `0xffffffff8006bc2a`, `progress=site-change`; recent symbols include `vsprintf.c`/`printk_ringbuffer.c` | Live-slow kernel logging/formatting lane in this run; old child-exit classification is historical unless reproduced. |
| `557.xz_r` | `live-timeout` | count `36000000010`, BPC `0x155558d6da`, last `progress=same-site` but count still advances | Same-site live-slow lane. Use shorter heartbeat interval or PC-watch around `0x155558d6da` before raising timeout. |
| `999.specrand_ir` | pass | `LINX_SPEC_PASS 999.specrand_ir`; FNV-1a `rand.11.out` hash `0x973dcfc2` matches | smoke sentinel closed |

The shared-runtime diagnostic run in
`workloads/generated/specint-train-all-20260628-after-kstat/` currently fails
all ten benchmarks quickly, including `999.specrand_ir`. That route is useful
for loader/libc diagnosis but is not the current SPEC correctness gate. The
static phase-b route is the baseline for benchmark correctness while shared
startup and C++ runtime packaging are being repaired.

The SPEC loop now records bounded failure classes and heartbeat-liveness fields
in both `stage_b_summary.json` and `qemu_matrix_summary.json`. The matrix and
fast-gate wrappers now also expose `--memory-mb` and record `memory_mb` in their
summaries, so resource-sensitive C++ rows can be reproduced without bypassing
the suite flow. A focused
`LINX_QEMU_HEARTBEAT_REGS=1` sentinel run proves the full-register heartbeat
switch without changing behavior: `999.specrand_ir` still passes and the QEMU
log contains `LINX_HEARTBEAT_REGS`. A separate
`LINX_DEBUG_PC_WATCH_REGS=1` smoke proves focused watchpoints can now emit
`LINX_PC_WATCH_REGS` full-GPR records. The new
`LINX_QEMU_HEARTBEAT_CODE_BYTES=16` sentinel run also passes
`999.specrand_ir` and emits `LINX_HEARTBEAT_CODE` records with PC/BPC bytes.
The new `LINX_DEBUG_PC_WATCH_DUMP_REGS=sp,tp,a0` sentinel run passes
`999.specrand_ir` and emits three same-hit guest-word dumps, so allocator and
list traces can capture multiple pointer sources in one long run. The new
`LINX_DEBUG_PC_WATCH_DUMP_OFFSETS=0,8` sentinel also passes
`999.specrand_ir` and emits multiple offsets from one pointer source in a single
hit; focused 500 runs use the same switch to capture several Perl range-frame
slots without rerunning the billion-instruction window. The new
`LINX_DEBUG_PC_WATCH_DUMP_WIDTH=4` sentinel also passes strict
`999.specrand_ir` and emits `width=4` stack words, giving focused runs a
field-width probe for 32-bit flags without changing default 8-byte logs.
The new `LINX_DEBUG_PC_WATCH_DUMP_PTR_OFFSETS=0` sentinel also passes strict
`999.specrand_ir` and emits one-hop pointer-slot dumps such as
`sp+0x0->0x7ffff000`, so focused SPEC runs can keep source slots and pointee
fields in one QEMU log.
The new `LINX_DEBUG_PC_WATCH_DUMP_CALL_RING=1` switch dumps the existing
`LINX_CALL_TRACE_RING=1` call/return ring when a watched PC fires. A focused
8 GiB `999.specrand_ir` panic probe stops at `panic()` before the delay loop
and records the caller path from `schedule()` plus the panic string argument,
which separates first-cause kernel panic evidence from later heartbeat churn.

2026-06-29 QEMU profile update: the queue fast path inlines scalar queue reads
and TQ/UQ pushes when `LINX_DEBUG_LOCAL` is not enabled. The focused
`500.perlbench_r` sample at
`workloads/generated/specint-profile-500-queue-inline-20260629-r2/profile/qemu-500-queue-inline.sample.txt`
shows `helper_linx_scalar_read_reg`, `helper_linx_tq_push`, and
`helper_linx_uq_push` at zero samples. That exposed `helper_linx_heartbeat` as
the next artificial top frame because it still ran once per translated block
even with a 1B-instruction interval. The heartbeat guard adds
`heartbeat_next_count` to the CPU state and skips the helper in translated code
until the next configured bucket. The follow-up sample at
`workloads/generated/specint-profile-500-queue-inline-hbguard-20260629-r1/profile/qemu-500-queue-inline-hbguard.sample.txt`
shows `helper_linx_heartbeat` at zero samples. Remaining top frames are
`helper_linx_tile_set_attr`, `helper_linx_tile_reset_block`,
`helper_linx_template_step`,
`helper_linx_check_bstart_target`, `linx_is_bstart_at_addr`, and
`probe_access_flags`.

Proposed next fixes:

1. Keep the QEMU heartbeat disabled by default, but enable it on long train
   runs to distinguish live progress from deadlock. Use BPC/PC churn plus
   `progress` and `same_site` before increasing timeouts.
2. Keep the old `502.gcc_r` byval compiler lane closed, but treat current 502
   as a Linux VM correctness blocker. Add temporary kernel-side tracepoints or
   `pr_info_once` guards around `do_mprotect_pkey()` and `do_page_fault()` for
   `0x3f7fa8d000..0x3f7fa8dfff`: log VMA start/end/flags, return value,
   `find_vma()` result, `access_error()`, and `handle_mm_fault()` flags. The
   QEMU page-walk evidence already proves the store sees a type0 PTE, so do not
   change QEMU TLB invalidation policy unless the kernel trace shows valid VMA
   coverage and a newly installed writable PTE.
3. Keep the old `500.perlbench_r` BigInt and bad-branch-target failures closed.
   The current static 500 row is run_001 hash pass plus run_002 live timeout, so
   it belongs in the QEMU throughput lane unless a fresh current run reproduces a
   trap.
4. Reclassify the current C++ rows from wrapper child-exit to live-slow unless a
   fresh run reproduces `sig=9`. In the latest all-train matrix,
   `520.omnetpp_r`, `523.xalancbmk_r`, and `541.leela_r` all reach
   heartbeat-backed kernel string/formatting or memory-management sites. Profile
   those rows with a coarser heartbeat or heartbeat disabled, then sample QEMU
   helper hot spots and kernel symbolized BPCs before changing compiler or C++
   runtime code.
5. Treat `525.x264_r` as an initramfs packaging/rootfs-size panic sentinel in
   this flow. The latest initramfs row panics before useful heartbeat evidence
   with `VFS: Unable to mount root fs`; use 9p or a disk/rootfs transport for
   benchmark execution after preserving this panic as a separate rootfs test.
6. Profile live-slow rows with heartbeat off or at a very coarse interval:
   `500.perlbench_r`, `505.mcf_r`, `520.omnetpp_r`, `523.xalancbmk_r`,
   `531.deepsjeng_r`, `541.leela_r`, `557.xz_r`, plus 9p `999.specrand_ir` as a
   transport sentinel. Keep `502.gcc_r` in the Linux VM correctness lane until
   the `mprotect()`/page-fault mismatch is closed. Remaining QEMU
   speedups should focus on
   tile set/reset, template stepping, page-local BSTART decode caching,
   TB chaining, `helper_linx_check_bstart_target`, `linx_is_bstart_at_addr`, and
   avoiding helper probes in hot branch-validation paths. Queue/scalar helper
   overhead, heartbeat helper overhead, and scalar no-op tile commit overhead
   are already closed by the queue-inline, heartbeat-guard, and tile-commit
   guard patches.
7. Use count-windowed diagnostics for late SPEC windows. Pair
   `LINX_FAULT_TRACE_COUNT_LO/HI`, `LINX_DEBUG_PC_WATCH_COUNT_LO/HI`,
   `LINX_MEM_TRACE_COUNT_LO/HI`, and `LINX_TLB_FILL_TRACE_COUNT_LO/HI` with
   PC/ACR/address filters so early boot or early stack-slot reuse does not
   consume trace quotas before the final fault.
8. Keep `train-all` opt-in through `--profile train`; the PR gate should stay on
   cheap `999.specrand_ir` smoke while stress workloads run in isolated nightly
   or diagnostic lanes.

## 2026-06-29 500 BigInt Current Evidence

`500.perlbench_r` now reaches Perl user code deterministically and fails in the
`Math::BigInt` train input, not in Linux dentry lookup and not in SPEC input
packaging. Host `/usr/bin/perl -I./lib perfect.pl b 3` passes in the same run
directory. Ignored, temporary `Devel::Peek` instrumentation immediately before
the failing `1 .. $count` range observed `$count` as a plain scalar with
`FLAGS = (IOK,pIOK)` and `IV = 2`; the source line still dies with
`Range iterator outside integer range`. A Linx C micro-smoke for the
`SVf_IOK|SVf_IVisUV` guard compiles correctly at both `-O0` and `-O2`, so the
visible `andiw 32` in the `pp_flop` window is not a standalone IVisUV mask bug.

Focused PC-watch evidence:

- `workloads/generated/specint-500-ppflop-offsets-20260629-r1/` proves
  multi-offset frame snapshots preserve the same failure class.
- `workloads/generated/specint-500-ppflop-sv-objects-20260629-r2/` captures
  final `pp_flop` GPR and object-word state before the exception.
- `workloads/generated/specint-500-ppflop-width4-watch-20260629-r1/` uses the
  new 4-byte dump width to expose flag-sized lanes in the same deterministic
  failure window.
- `workloads/generated/specint-500-ppflop-branch-ptrslots-20260629-r1/` uses
  `LINX_DEBUG_PC_WATCH_DUMP_PTR_OFFSETS` to dereference selected `pp_flop`
  frame/object slots in the same window. The final watched error-build block
  records `pc=0x1555829792`, `a2=0x2`, and pointer slots such as
  `sp+0x30->0x155588a9b0` plus `s0+0x10->0x1555847268`.
- `workloads/generated/specint-500-ppflop-branch-countwin-20260629-r1/`
  removes the per-PC hit filter and watches the final count window
  `3069000000..3072000000`. It records repeated `0x1555829792` then
  `0x15558297ae` pairs and no watched `0x15558297d4` continuation before the
  `Range iterator outside integer range` exit.

Next solution path: keep 500 out of the deadlock and dcache lanes. The current
blocker is an active `pp_flop` error-path decision: the optimized branch builds
the croak message at runtime `0x1555829792` and enters `Perl_croak` at
`0x15558297ae`, while the watched final window does not reach the post-croak
continuation at `0x15558297d4`. Compare the Linx `pp_ctl.c` optimized
conditions and SV slots against host behavior with a selective compile/probe
before changing SPEC packaging or QEMU control-flow rules.

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
   lib/Math/BigInt.pm line 2675` investigation from
   `workloads/generated/specint-500-ppflop-offsets-20260629-r1/`,
   `workloads/generated/specint-500-ppflop-sv-objects-20260629-r2/`, and
   `workloads/generated/specint-500-ppflop-branch-countwin-20260629-r1/`. Map
   the captured `pp_flop` frame/register state to Perl SV flag/value fields,
   then minimize a Linx-native scalar/range smoke before changing SPEC
   packaging or QEMU control-flow rules.

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
2. Treat the BigInt user-code stop captured by
   `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/` as
   historical root-cause evidence; the Linx LLVM f64 extload fix closes that
   class. The current 500 path is the run_002 branch-target trap in
   `workloads/generated/specint-train-all-queue-inline-hbguard-20260629-r1/`,
   so the next loop should inspect the symbolized musl `__syscall_cp_c` /
   `sccp` origin before changing kernel/QEMU liveness policy.
3. Keep the v0.56 fixup parser as a prerequisite for all uaccess-heavy SPEC
   work; without it, normal faultable usercopy recovery is misclassified as an
   unhandled kernel page fault.

## Next Speedups

Current train-all live-progress evidence:

- `workloads/generated/specint-train-all-queue-inline-hbguard-20260629-r1/initramfs/stage_b_summary.json`
  is the current all-train ledger. The live timeout rows are `502`, `505`,
  `520`, `523`, `525`, `531`, `541`, and `557`; all have
  `heartbeat_running=true`, `heartbeat_site_progress=true`, and no panic or
  user trap. `500.perlbench_r` has split out of the live-slow lane: run_001
  passes `perfect.b.3.out` by hash, while run_002 traps at a bad branch target
  after entering musl `__syscall_cp_c` / `sccp`.
- Fresh macOS samples:
  `workloads/generated/specint-profile-500-queue-inline-20260629-r2/profile/qemu-500-queue-inline.sample.txt`
  and
  `workloads/generated/specint-profile-500-queue-inline-hbguard-20260629-r1/profile/qemu-500-queue-inline-hbguard.sample.txt`.
  The first sample proves scalar queue reads and TQ/UQ push helpers are gone
  from the hot path. The second proves `helper_linx_heartbeat` is also gone
  from the hot path. Remaining top-of-stack cost is concentrated in
  `helper_linx_tile_commit`, `helper_linx_tile_set_attr`,
  `helper_linx_tile_reset_block`, `helper_linx_template_step`,
  `helper_linx_check_bstart_target`, `linx_is_bstart_at_addr`, and
  `probe_access_flags`.
- Older macOS `sample` captures under
  `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/profile/`
  for `523.xalancbmk_r`, `531.deepsjeng_r`, and `557.xz_r` show the same broad
  helper families. The latest samples remove queue/scalar helper traffic and
  heartbeat overhead as active explanations; remaining cost is
  tile/template/BSTART/probe/TLB work.

Prioritized QEMU speedups:

1. Fast-path disabled trace helpers out of hot loops. The call-trace ring path
   now initializes once per event and returns immediately when both text trace
   and ring trace are disabled. `linx_trace_capture_active()` now avoids the
   generic active helpers on every writeback and reads cached
   commit/minst/cosim state after one-time init.
2. Add a page-local BSTART decode cache with explicit TB/text invalidation.
   Positive target caching reduces repeated hits, but cold or colliding targets
   still decode through the helper probe and BSTART byte classification.
3. Reduce helper traffic in the tile/template hot path. Simple scalar queue
   reads and pushes are now inlined into generated TCG, so the next speed lane
   should inline or fuse the common tile commit/set/reset and template-step
   sequence, then retest against the all-train live-slow rows.
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
