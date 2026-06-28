# SPECint / QEMU Checklist

## Live Blockers (2026-06-29)

- [x] ID: SPEC-M01F Train-all gate shape exists and covers every current Linx SPECint rate benchmark.
  Static build command: `MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh && ./tools/build_linx_llvm_cpp_runtimes.sh --profile spec --mode phase-b && LINX_SPEC_FORCE_STATIC=1 bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --emit-manifest workloads/generated/specint-build-after-oldmalloc-20260628/build_manifest_final.json`
  Static run command: `SPECINT_TRAIN_ALL_TIMEOUT=300 LINX_SPEC_HEARTBEAT_SEC=30 LINX_SPEC_QEMU_HEARTBEAT_INTERVAL=1000000000 LINX_SPEC_NO_PROGRESS_TIMEOUT=180 python3 tools/bringup/run_specint_fast_gate.py --profile train --out-dir workloads/generated/specint-train-all-20260628-after-oldmalloc --qemu emulator/qemu/build-linx/qemu-system-linx64 --append-extra norandmaps --guest-heartbeat-sec 0 --heartbeat-sec 30 --qemu-heartbeat-interval 1000000000 --no-progress-timeout 180 --continue-on-fail`
  Evidence: `workloads/generated/specint-build-after-oldmalloc-20260628/build_manifest_final.json`, `out/cpp-runtime/musl-cxx17-spec/summary_phase-b.json`, `avs/qemu/out/musl-static-oldmalloc-page-20260628/summary.json`, `workloads/generated/specint-train-all-20260628-after-oldmalloc/specint_fast_gate_summary.json`, `workloads/generated/specint-train-all-20260628-after-oldmalloc/train-all/qemu_matrix_summary.json`, and `workloads/generated/specint-train-all-20260628-after-oldmalloc/train-all/initramfs/stage_b_summary.json`.
  Status: suite wiring covers `500.perlbench_r`, `502.gcc_r`, `505.mcf_r`, `520.omnetpp_r`, `523.xalancbmk_r`, `525.x264_r`, `531.deepsjeng_r`, `541.leela_r`, `557.xz_r`, and `999.specrand_ir`.
  Static build result: all ten selected C/C++ benchmarks built as Linx executables; source immutability check passed.

- [x] ID: SPEC-M05-LATEST-TRAIN-ALL-20260629 Latest train-all failure ledger is current.
  Command: `SPEC_QEMU_HEARTBEAT_INTERVAL=50000000 SPEC_GUEST_HEARTBEAT_SEC=0 SPEC_NO_PROGRESS_TIMEOUT=180 python3 tools/bringup/run_specint_fast_gate.py --profile train --continue-on-fail --qemu emulator/qemu/build-linx/qemu-system-linx64 --sysroot out/libc/musl/install/phase-b --out-dir workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1 --append-extra norandmaps --heartbeat-sec 30 --qemu-heartbeat-interval 50000000 --guest-heartbeat-sec 0 --no-progress-timeout 180`
  Evidence: `workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1/specint_fast_gate_summary.json`, `workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1/train-all/qemu_matrix_summary.json`, and `workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1/train-all/initramfs/stage_b_summary.json`.
  Result: `ok=false`, elapsed `909.005s`; `999.specrand_ir` passes strict hash. Every failed benchmark has `heartbeat_running=true` and `heartbeat_site_progress=true`, so the current failures are not global QEMU deadlocks. The same-ACR `x1` frame fix remains stable, and the refreshed post-PC-watch-offset QEMU run keeps `500.perlbench_r` on the Perl BigInt range blocker instead of the old `__d_lookup_rcu` Oops.

  | Benchmark | Status | Latest evidence | Proposed owner / next step |
  | --- | --- | --- | --- |
  | `500.perlbench_r` | `user-arithmetic-range` | `Range iterator outside integer range at lib/Math/BigInt.pm line 2675`; no panic/trap; count `3350000008`, BPC `0x15556193a0` | Dlookup Oops is closed. Current owner is Perl scalar/range correctness. |
  | `502.gcc_r` | `user-trap` | trap `addr=0x305910060a11b059`, user `tpc=0x15559baa04`, `bpc=0x15559ba9fc`, `orig_tpc=0x1556076d02`, `orig_bpc=0x1556076ce4`; count `5700000005`, BPC `0xffffffff803dde02` | The stack limit is now effective (`stack-limit=268435456`) but the same GCC user trap remains; continue with fault regs/code bytes around the new user BPC path and the brk/mmap allocator evidence. |
  | `505.mcf_r` | `live-timeout` | count `34900000001`, BPC `0x155555c430`, recent unique sites `7`, `progress=site-change` | Treat current train input as throughput/live-progress. Reproduce older user traps before moving it back to correctness. |
  | `520.omnetpp_r` | `user-trap` | null trap at `tpc=0xeaea2`, `bpc=0xeae90`, count `750000002`, BPC `0xffffffff803dde02` | Continue as C++ object/callback correctness. Use fault regs plus call trace around the section/config path. |
  | `523.xalancbmk_r` | `user-trap` | trap `addr=0x3feffffff8`, user `tpc=0x1555a6306a`, `bpc=0x1555a6306a`, count `10350000000`, BPC `0xffffffff80069ff6` | Reclassify from live-slow to correctness under effective finite stack. Use fault regs/code bytes around the C++ user trap. |
  | `525.x264_r` | `live-timeout` | count `20800000000`, BPC `0xffffffff800019bc`, `stalled=false` | Current owner is throughput/live progress; the older panic is historical unless it reappears. |
  | `531.deepsjeng_r` | `live-timeout` | count `30850000002`, BPC `0x1555560764`, recent unique sites `8`, `progress=site-change` | Current train input is slow/live. Use a focused profile and compare against the earlier test-input pass profile to find remaining QEMU hot helpers. |
  | `541.leela_r` | `user-trap` | trap `addr=0x3feffffff8`, user `tpc=0x1555623796`, `bpc=0x1555623796`, count `5950000001`, BPC `0xffffffff803dde02` | Group with the C++/stack-edge user traps, not live-slow. |
  | `557.xz_r` | `live-timeout` | count `30550000006`, BPC `0x155558d612`, recent unique sites `5`, `progress=site-change` | Current train input is slow/live. Profile before pursuing older bad-pointer evidence. |
  | `999.specrand_ir` | pass | strict hash `0x973dcfc2`, count `450000001`, BPC `0xffffffff803dde02`; focused raw-prlimit and PC-watch-offset smokes also pass | Keep as the cheap QEMU debug sentinel. |

- [x] ID: SPEC-M05-STACKLIMIT-SYSCALL SPEC wrapper stack-limit control bypasses the libc `setrlimit()` return bug.
  Resolution: generated init wrappers use a raw Linx `prlimit64` syscall for `RLIMIT_STACK` before falling back to libc `setrlimit()`. `LINX_SPEC_STACK_LIMIT_BYTES=<n>` overrides the default 256 MiB value; `LINX_SPEC_STACK_LIMIT_BYTES=unlimited` preserves the old unlimited-stack reproduction mode.
  Evidence: `workloads/generated/specint-999-prlimit-trace-20260629-r1/initramfs/999_specrand_ir/run_001/qemu.log` shows syscall `261` returning `0` while libc `setrlimit()` still warns `errno=21`. `workloads/generated/specint-999-raw-prlimit-20260629-r1/initramfs/999_specrand_ir/run_001/qemu.log` shows syscall `261` returning `0`, `LINX_SPEC_DBG stack-limit=268435456`, no `setrlimit-stack` warning, and strict hash pass. `workloads/generated/specint-502-raw-prlimit-20260629-r1/initramfs/502_gcc_r/run_001/qemu.log` also logs `stack-limit=268435456`.
  Follow-up: keep a separate libc task for why musl `setrlimit()` reports `errno=21` after a successful `prlimit64`; the SPEC gate no longer depends on that wrapper for stack layout control.

- [x] ID: SPEC-M05-LATEST-TRAIN-ALL-20260628 Latest train-all failure ledger is current.
  Command: `LINX_QEMU_HEARTBEAT_CODE_BYTES=0 SPECINT_TRAIN_ALL_TIMEOUT=180 SPEC_GUEST_HEARTBEAT_SEC=0 SPEC_QEMU_HEARTBEAT_INTERVAL=50000000 SPEC_NO_PROGRESS_TIMEOUT=120 python3 tools/bringup/run_specint_fast_gate.py --profile train --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 --qemu emulator/qemu/build-linx/qemu-system-linx64 --sysroot out/libc/musl/install/phase-b --out-dir workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1 --append-extra norandmaps --continue-on-fail --heartbeat-sec 30 --qemu-heartbeat-interval 50000000 --guest-heartbeat-sec 0 --no-progress-timeout 120`
  Evidence: `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/specint_fast_gate_summary.json`, `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/qemu_matrix_summary.json`, and `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/stage_b_summary.json`.
  Result: `ok=false`, elapsed `729.231s`; no failed benchmark was classified as `stalled`, and every failed benchmark had `heartbeat_running=true` plus `heartbeat_site_progress=true`, so the current failures are not global QEMU deadlocks.

  | Benchmark | Status | Latest evidence | Proposed owner / next step |
  | --- | --- | --- | --- |
  | `500.perlbench_r` | `user-arithmetic-range` | `Range iterator outside integer range at lib/Math/BigInt.pm line 2675`, count `3350000001`, BPC `0x15556ec224` | Minimize a Linx Perl scalar/range smoke and compare compiler/QEMU scalar IV/NV flag behavior before changing SPEC packaging. |
  | `502.gcc_r` | `user-trap` | `addr=0x10`, user `tpc=0x1556074e88`, user `bpc=0x1556074e80`, count `5650000001`, BPC `0xffffffff801f346c`; focused traces show `brk(0x1556273000) -> 0x1556273000`, later `brk(0x1556277000) -> 0x1556273000`, fallback `mmap(0, 0x1ba000, ...) -> 0x1556273000`, and overlapping chunks at `0x1556276010/0x1556276030` | EBADF is resolved by the QEMU predicated CALL skip fix. Current owner remains the allocator/VM boundary around the brk frontier: separate normal anonymous mmap placement from oldmalloc's fallback heap-extension mmap. |
  | `505.mcf_r` | `user-trap` | `addr=0x19`, user `tpc=0x155555b860`, user `bpc=0x155555b85a`, count `1300000010`, BPC `0xffffffff800fb0ba` | Treat as a correctness trap again, not throughput. Use fault-regs plus code-byte PC-watch around `primal_net_simplex`/stdio closeout and compare the open-file/list state before the final bad pointer. |
  | `520.omnetpp_r` | `user-trap` | null address trap at `tpc=0xeaea2`, `bpc=0xeae90`, count `750000003`, BPC `0xffffffff803dde02` | Continue as C++ object/callback correctness, not liveness; symbolize the section/config path and inspect static C++ ABI/state. |
  | `523.xalancbmk_r` | `live-timeout` | count `27850000004`, BPC `0xffffffff80090c62`, recent unique heartbeat sites `6`, `stalled=false` | Profile with heartbeat off/coarse, then target BSTART decode/cache and hot helper overhead; also symbolize the recurring kernel breadcrumb. |
  | `525.x264_r` | `live-timeout` | count `24050000000`, BPC `0xffffffff803e8f46`, recent unique heartbeat sites `4`, `stalled=false` | Latest run no longer reproduces the prior early panic; treat current blocker as throughput/live progress first, while keeping the older panic caller as historical evidence if it returns. |
  | `531.deepsjeng_r` | `user-trap` | branch-target trap with `tpc=0`, `bpc=0`, `bpcn=0x1555576390`, count `6700000005`, BPC `0xffffffff800fc628` | Focus branch-target legality/call-ret state with fault regs, call-trace ring, and PC-watch code bytes around the symbolized user path. |
  | `541.leela_r` | `live-timeout` | count `11850000002`, BPC `0xffffffff80090e84`, recent unique heartbeat sites `8`, `stalled=false` | Same performance lane as `523`/`525`; reduce QEMU overhead after correctness traps are separated. |
  | `557.xz_r` | `user-trap` | bad address `0x04000415794a241f`, user `tpc=0x155557fae8`, user `bpc=0x155557fada`, count `9050000000`, BPC `0xffffffff800fba2c` | Treat as pointer/control-flow corruption; symbolize failing block and compare compiler/QEMU branch and memory state. |
  | `999.specrand_ir` | pass | strict hash `0x973dcfc2`, count `450000004`, BPC `0xffffffff803dde92` | Keep as the cheap train pass sentinel for QEMU debug changes. |

- [x] ID: SPEC-QEMU-HB-001 BPC heartbeat switch exists.
  Switches: `LINX_HEARTBEAT_INTERVAL` or `LINX_QEMU_HEARTBEAT_INTERVAL`; fast-gate option `--qemu-heartbeat-interval`. Focused register snapshots use `LINX_HEARTBEAT_REGS=1` or `LINX_QEMU_HEARTBEAT_REGS=1`. Focused code-byte snapshots use `LINX_HEARTBEAT_CODE_BYTES=<n>` or `LINX_QEMU_HEARTBEAT_CODE_BYTES=<n>`.
  Done means: qemu logs emit `LINX_HEARTBEAT` with count, delta, PC, BPC, TPC, branch state, `progress=first|site-change|same-site`, `same_site`, TP/ETEMP breadcrumbs, stack/return registers, and selected argument registers. Optional companion records emit full GPRs or PC/BPC code bytes.
  Evidence: `workloads/generated/specint-heartbeat-smoke-20260628/test-smoke/initramfs/999_specrand_ir/run_001/qemu.log`, the rebuilt-QEMU train-all runs under `workloads/generated/specint-train-all-20260628-qemu-context-r1/train-all/initramfs/` and `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/`, `workloads/generated/specint-heartbeat-regs-smoke-20260628/initramfs/999_specrand_ir/run_001/qemu.log`, and `workloads/generated/specint-heartbeat-code-smoke-20260628-r1/initramfs/999_specrand_ir/run_001/qemu.log`.
  Result: the rebuilt-QEMU train-all run marks no failed benchmark as `stalled`; every failed benchmark has `heartbeat_running=true` and `heartbeat_site_progress=true`, so the current failures are traps or live slow paths rather than global QEMU deadlocks. The focused heartbeat-register smoke passes `999.specrand_ir` and emits `LINX_HEARTBEAT_REGS`; the focused heartbeat-code smoke passes `999.specrand_ir` and emits `LINX_HEARTBEAT_CODE`.

- [x] ID: SPEC-QEMU-TP-DBG-001 TP handoff tracing is available for focused SPEC and musl runs.
  Switches: `LINX_TP_TRACE=1`, optional `LINX_TP_TRACE_LIMIT`, `LINX_TP_TRACE_SSR=1`, and `LINX_TP_TRACE_READS=1`.
  Done means: qemu logs emit `LINX_TP_TRACE` records for service-request, sync-trap, IRQ, same-ACR frame setup, and ACRE handoff points, with user TP, kernel thread-info TP, ETEMP/ETEMP0 breadcrumbs, BPC/TPC, saved `x1` for same-ACR frames, and selected GPRs.
  Evidence: `avs/qemu/out/musl-tp-preserve-debug-r2-20260628/summary.json` passes and its qemu log includes `LINX_TP_TRACE event=service_user_to_kernel`; focused `523.xalancbmk_r` tracing under `workloads/generated/specint-523-tp-trace-20260628/run/` separated the old C++ startup TP issue from later stack-limit/throughput stops. Same-ACR frame events are implemented as `sync_same_acr_frame` and `irq_same_acr_frame` and are covered indirectly by the post-fix AVS/system and SPEC 500 runs.

- [x] ID: SPEC-QEMU-SYSCALL-DBG-001 Syscall trace can identify path/fd failures without full traces.
  Switches: `LINX_SYSCALL_TRACE=1`, optional `LINX_SYSCALL_TRACE_NR`, `LINX_SYSCALL_TRACE_PC_LO/HI`, `LINX_SYSCALL_TRACE_LIMIT`, `LINX_SYSCALL_TRACE_STRINGS=1`, `LINX_SYSCALL_TRACE_STRING_MAX`, `LINX_SYSCALL_TRACE_REGS=1`, and shared `LINX_TRACE_REGS=1`.
  Done means: qemu logs emit syscall entry/return pairs, entry arguments on returns, unpaired syscall markers, separate `LINX_SYSCALL_ARGSTR` records for pathname arguments, and opt-in `LINX_SYSCALL_REGS` full-GPR records.
  Evidence: `workloads/generated/specint-502-syscall-argstr-smoke-20260628/run/initramfs/502_gcc_r/run_001/qemu.log` contains `LINX_SYSCALL_ARGSTR` records for `/dev/console`, `/spec-run`, SPEC output/input paths, and `.linx_empty_stdin`.

- [x] ID: SPEC-QEMU-FAULT-DBG-001 Fault trace can dump full Linx register state.
  Switches: `LINX_FAULT_TRACE=1`, `LINX_FAULT_TRACE_REGS=1`, optional `LINX_FAULT_TRACE_LIMIT`, and shared `LINX_TRACE_REGS=1`.
  Done means: qemu logs emit `LINX_FAULT_REGS` after a synchronous fault with all GPRs, BPC/TPC context, and instruction count.
  Evidence: `workloads/generated/specint-cxx-after-oldmalloc-20260628/run/initramfs/520_omnetpp_r/run_001/qemu.log`, `workloads/generated/specint-cxx-after-oldmalloc-20260628/run/initramfs/523_xalancbmk_r/run_001/qemu.log`, and `workloads/generated/specint-cxx-after-oldmalloc-20260628/run/initramfs/541_leela_r/run_001/qemu.log`.

- [x] ID: SPEC-QEMU-PCWATCH-DBG-001 PC watch can dump full Linx register state and deferred ring snapshots.
  Switches: `LINX_DEBUG_PC_WATCH=<pc>[,<pc>...]`, `LINX_DEBUG_PC_WATCH_REGS=1`, `LINX_DEBUG_PC_WATCH_DUMP_CODE_BYTES=<n>`, optional `LINX_DEBUG_PC_WATCH_EXIT=1`, count filters `LINX_DEBUG_PC_WATCH_COUNT_LO=<insns>` / `LINX_DEBUG_PC_WATCH_COUNT_HI=<insns>`, hit filters `LINX_DEBUG_PC_WATCH_HIT_LO=<n>` / `LINX_DEBUG_PC_WATCH_HIT_HI=<n>`, print cap `LINX_DEBUG_PC_WATCH_HIT_LIMIT=<n>`, GPR value match filter `LINX_DEBUG_PC_WATCH_MATCH_GPR=<gpr>` plus `LINX_DEBUG_PC_WATCH_MATCH_VALUE=<value>` and optional `LINX_DEBUG_PC_WATCH_MATCH_MASK=<mask>`, memory dump source `LINX_DEBUG_PC_WATCH_DUMP_REG=<gpr|tp|tqN|uqN|t#N|u#N>`, memory dump source list `LINX_DEBUG_PC_WATCH_DUMP_REGS=<reg>[,<reg>...]`, `LINX_DEBUG_PC_WATCH_DUMP_WORDS=<n>`, `LINX_DEBUG_PC_WATCH_DUMP_OFFSET=<bytes>`, multi-slot offset list `LINX_DEBUG_PC_WATCH_DUMP_OFFSETS=<bytes>[,<bytes>...]`, backward-compatible `LINX_DEBUG_PC_WATCH_DUMP_A0_WORDS=<n>` / `LINX_DEBUG_PC_WATCH_DUMP_A0_OFFSET=<bytes>`, `LINX_DEBUG_PC_WATCH_PRINT=0`, `LINX_DEBUG_PC_WATCH_RING=1`, `LINX_DEBUG_PC_WATCH_RING_SIZE=<1..128>`, ring memory source `LINX_DEBUG_PC_WATCH_RING_MEM_REG=<gpr|tp|tqN|uqN|t#N|u#N>`, ring memory offset `LINX_DEBUG_PC_WATCH_RING_MEM_OFFSET=<bytes>`, and shared `LINX_TRACE_REGS=1`.
  Done means: qemu logs emit `linx_pc_watch:` plus optional `LINX_PC_WATCH_REGS` with all GPRs, BPC/TPC context, instruction count at a focused PC, optional `LINX_PC_WATCH_CODE` bytes for symbolizing ambiguous runtime mappings, optional memory words from one or more selected register/queue pointers, and `printed=<n>` so noisy symbols can be capped without hiding total hits. Ring-only mode records matching hits after filters pass and emits `LINX_PC_WATCH_RING` / `LINX_PC_WATCH_RING_ENTRY` records when `LINX_FAULT_TRACE` catches a synchronous fault; ring entries can also include a non-perturbing guest memory snapshot from a selected pointer source.
  Evidence: `workloads/generated/specint-pcwatch-regs-smoke-20260628-r1/initramfs/999_specrand_ir/run_001/qemu.log` contains `LINX_PC_WATCH_REGS` for watched PC `0xffffffff80404da6`; `workloads/generated/specint-pcwatch-filter-smoke-20260628-r1/999_specrand_ir/run_001/qemu.log` passes `999.specrand_ir` and contains a filtered `linx_pc_watch:` record with `printed=1 count=655930`; `workloads/generated/specint-pcwatch-dump-regs-smoke-20260628-r1/initramfs/999_specrand_ir/run_001/qemu.log` passes `999.specrand_ir` and proves `LINX_DEBUG_PC_WATCH_DUMP_REGS=sp,tp,a0` emits three same-hit memory dumps; `workloads/generated/specint-pcwatch-dump-offsets-smoke-20260629-r1/initramfs/999_specrand_ir/run_001/qemu.log` passes `999.specrand_ir` and proves `LINX_DEBUG_PC_WATCH_DUMP_OFFSETS=0,8` emits both `sp+0x0` and `sp+0x8` in one hit; `workloads/generated/specint-502-alloc-pcwatch-a2-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` proves `LINX_DEBUG_PC_WATCH_DUMP_REG=a2` dumps allocator chunk words; `workloads/generated/specint-502-alloc-pcwatch-match-a2-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` proves `MATCH_GPR=a2`/`MATCH_VALUE=0x1556276030` isolates the final allocator trap chunk; `workloads/generated/specint-500-pcwatch-ring-a1-20260629-r1/500_perlbench_r/run_001/qemu.log` proves ring-only PC-watch preserves the 500 kernel-panic path while dumping the final dentry compare state; `workloads/generated/specint-500-pcwatch-ring-mem-a1-20260629-r1/500_perlbench_r/run_001/qemu.log` proves ring memory snapshots can show `x1=0x1` while `[a1+0x20]` still contains `0xff60000004c02db8`.

- [x] ID: SPEC-QEMU-MEMTRACE-DBG-001 Memory trace can target loads or stores without instrumenting the opposite access class.
  Switches: `LINX_MEM_TRACE_ADDR=<addr>`, optional `LINX_MEM_TRACE_SIZE=<bytes>`, `LINX_MEM_TRACE_LIMIT=<n>`, `LINX_MEM_TRACE_PC_LO=<pc>`, `LINX_MEM_TRACE_PC_HI=<pc>`, `LINX_MEM_TRACE_ACCESS=loads|stores|all`, `LINX_MEM_TRACE_ACR=<0..15>`, `LINX_MEM_TRACE_CONTEXT=1`, and `LINX_MEM_TRACE_FAST=0` to disable the translated fast overlap guard.
  Done means: qemu logs emit `LINX_MEM_TRACE` for overlapping memory accesses, `LINX_MEM_TRACE_ACCESS=stores` emits only store helpers at translation time so long SPEC runs can trace heap metadata without load-helper overhead, `LINX_MEM_TRACE_ACR` filters to user or kernel ACR, and `LINX_MEM_TRACE_CONTEXT=1` appends `mmu_idx`, `ttbr0`, `ttbr1`, and `tcr`. With the default fast path, translated code skips the helper call unless an access overlaps the watched range.
  Evidence: `workloads/generated/specint-502-alloc-memtrace-store-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` captures stores to `0x1556276048`; `workloads/generated/specint-502-bin39-head-memtrace-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` captures bin 39 head writes; `workloads/generated/specint-502-chunk-next-memtrace-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` captures writes to chunk link `0x1556276020`; `workloads/generated/specint-502-free-overlap-memtrace-context-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` proves `LINX_MEM_TRACE_ACR=2` and `LINX_MEM_TRACE_CONTEXT=1` keep the overlapping free-list stores in one user address space; `workloads/generated/specint-502-memtrace-context-smoke-20260628-r2/initramfs/502_gcc_r/run_001/qemu.log` proves the rebuilt QEMU emits the new context fields; `workloads/generated/specint-500-dentry-name-storetrace-fast-20260629-r1/500_perlbench_r/run_001/qemu.log` proves the fast overlap guard still captures the dentry name pointer store with context.

- [x] ID: SPEC-QEMU-FALL-CALL-001 Predicated FALL skip handles adjacent CALL/ICALL blocks.
  Resolution: QEMU now recognizes an adjacent call-like BSTART while resolving a predicated FALL skip, uses the following SETRET as the return continuation, and follows a direct return-continuation header to the semantic join block when present. This prevents skipped conditional calls from entering the callee or call-return body with stale arguments.
  Evidence: `python3 avs/qemu/run_callret_contract.py` passes the new `cond_skips_adjacent_hl_call` regression; `bash avs/qemu/check_system_strict.sh` passes; `workloads/generated/specint-502-after-call-skip-join-20260628-r1/stage_b_summary.json` moves `502.gcc_r` from the prior `Bad file number` stop to a later user trap at musl malloc `unbin`; `workloads/generated/specint-train-all-20260628-call-skip-join-r1/train-all/initramfs/stage_b_summary.json` confirms the same train-all behavior.
  Rejected: skipping to the SETRET target alone still executes the call-return body; skipping to the callee body keeps the original `fstat` fallback path corrupted.

- [x] ID: SPEC-M05-SMOKE `999.specrand_ir` train input passes under the all-train run.
  Evidence: `workloads/generated/specint-train-all-20260629-same-acr-x1-r1/train-all/initramfs/stage_b_summary.json` records `ok=true`, last heartbeat count `450000000`, BPC `0xffffffff803dde02`, and strict FNV-1a hash `0x973dcfc2` for `rand.11.out`. Older all-train runs under `workloads/generated/specint-train-all-20260628-*` also contain `LINX_SPEC_PASS 999.specrand_ir` and remain historical smoke evidence.
  Note: a shared-runtime rebuild made `999.specrand_ir` a 15 KiB dynamic executable and it trapped in shared startup; the static phase-b executable is the current correctness gate until shared SPEC runtime is green.

- [x] ID: SPEC-M05-GTOD-502 Legacy `gettimeofday` no longer poisons 502 diagnostics.
  Resolution: Linx VDSO syscall fallbacks now load the syscall number in `a7`, and `sys_gettimeofday()` uses a Linx-local `copy_to_user()` copyout instead of the current faulting 64-bit `put_user()` path.
  Evidence: `workloads/generated/specint-502-static-gettimeofday-copyout-20260628/run/initramfs/502_gcc_r/run_001/qemu.log` shows syscall `169` returning `0` after the focused fix, and `avs/qemu/out/musl-time-syscalls-20260628/summary.json` passes the focused musl `time_syscalls` sample.
  Follow-up: the remaining `502.gcc_r` EBADF diagnostic is no longer explained by syscall `169`; the full post-fix trace contains no `-EBADF` syscall returns.

- [x] ID: SPEC-M05-EXECVE-500 `500.perlbench_r` static PIE is present and readable before `execve`.
  Resolution: the original `errno=2` classification was narrowed by the init-wrapper pre-exec probe; the benchmark path is valid in the initramfs.
  Evidence: `workloads/generated/specint-500-preexec-20260628/initramfs/500_perlbench_r/run_001/qemu.log` shows `stat=0`, `open=6`, `read4=4`, and ELF magic `0x7f454c46`.
  Follow-up: prior focused runs and the current all-train run reached Perl user code and failed in `Math::BigInt` range handling; track that under `SPEC-M05-BIGINT-500`.

- [x] ID: SPEC-M05-FIXUP-500 Linx Linux recognizes v0.56 faultable usercopy fixup blocks.
  Resolution: `arch/linx/mm/extable.c` now accepts nonzero-offset 32-bit and 48-bit `BSTART.{STD,SYS,FP} FALL<, fixup_label>` fixup encodings before the legacy 128-bit block-header fallback.
  Evidence: `workloads/generated/specint-500-fixup-20260628/initramfs/500_perlbench_r/run_001/qemu.log` no longer stops at the earlier `sys_fcntl` usercopy `HL.BSTART.STD FALL` Oops.
  Verification: `run_linux_vmlinux_build_clean.sh --target vmlinux` rebuilt `kernel/linux/build-linx-fixed/vmlinux`; focused 500 rerun advanced to a different Oops.

- [x] ID: SPEC-M05-KMALLOC-500 `500.perlbench_r` completes the earlier `filelock_cache` slab-cache path.
  Resolution: the Linx curated init path now initializes the file-lock slab cache, moving past the prior `kmem_cache_alloc_noprof` null-cache fault.
  Evidence: `workloads/generated/specint-500-after-filelock-20260628/`, `workloads/generated/specint-500-syscall-openat-ret-20260628/`, and `workloads/generated/specint-500-stdin-empty-20260628/`.

- [x] ID: SPEC-M05-DLOOKUP-500 `500.perlbench_r` must stop corrupting the VFS dentry/name lookup path.
  Resolution: the Oops was not dentry memory corruption. QEMU same-ACR trap/IRQ entry did not save interrupted `x1` into the current bank's ETEMP while clearing live `x1` to zero, which Linux's kernel-origin entry path expects. QEMU now prepares that same-ACR frame before vectoring.
  Evidence: `workloads/generated/specint-500-baseline-20260629-r1/stage_b_summary.json` reproduces the original `__d_lookup_rcu` Oops. `workloads/generated/specint-500-pcwatch-ring-mem-a1-20260629-r1/500_perlbench_r/run_001/qemu.log` shows the decisive state: the final ring entries have live `x1=0x1`, but `[a1+0x20]` still reads `0xff60000004c02db8`, so the dentry name field is valid. `workloads/generated/specint-500-after-same-acr-x1-20260629-r1/stage_b_summary.json` and `workloads/generated/specint-train-all-20260629-same-acr-x1-r1/train-all/initramfs/stage_b_summary.json` no longer panic and classify 500 as `user-arithmetic-range`.
  Follow-up: keep the same-ACR `x1` frame covered by AVS; reopen this item only if `__d_lookup_rcu` reproduces.

- [ ] ID: SPEC-M05-BIGINT-500 `500.perlbench_r` must complete Perl train input.
  Current blocker: after the same-ACR `x1` fix, this is again the active 500 blocker.
  Evidence: `workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1/train-all/initramfs/stage_b_summary.json` classifies `500.perlbench_r` as `user-arithmetic-range` with `Range iterator outside integer range at lib/Math/BigInt.pm line 2675`; heartbeat was still running with site progress, count `3350000008`, and BPC `0x15556193a0`. The focused rerun `workloads/generated/specint-500-after-same-acr-x1-20260629-r1/stage_b_summary.json` reproduces the same class without a kernel panic. `workloads/generated/specint-500-ppflop-offsets-20260629-r1/initramfs/500_perlbench_r/run_001/qemu.log` proves `LINX_DEBUG_PC_WATCH_DUMP_OFFSETS` can capture multiple `pp_flop` stack/frame slots in the deterministic failure window while preserving the same child-exit class. `workloads/generated/specint-500-ppflop-sv-objects-20260629-r2/initramfs/500_perlbench_r/run_001/qemu.log` captures final `pp_flop` hits 423-425 with GPRs and heap-object words before the range exception. Older evidence in `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/stage_b_summary.json` and `workloads/generated/specint-500-bigint-debug-20260628-r1/stage_b_summary.json` shows the same BigInt failure before the dlookup regression. Host `/usr/bin/perl -I./lib perfect.pl b 3` in the same run directory exits 0 with the expected first three perfect numbers, so argv/input packaging is not the current owner.
  Perturbation note: ignored SPEC-library instrumentation in `workloads/generated/specint-500-bigint-debug-20260628-r2/` shifted the source line but did not expose a useful pre-range value; replacing the range expression with an `eval` wrapper in `workloads/generated/specint-500-bigint-debug-20260628-r3/` changed the symptom to live timeout at 180s with heartbeat count `20450000004`, BPC `0x15556f4116`, and `stalled=false`. Focused QEMU PC-watch runs around Perl range/scalar symbols are also perturbing: `workloads/generated/specint-500-pcwatch-20260628-r1/stage_b_summary.json` failed before exec with `errno=2` despite the generated CPIO list containing the benchmark, and `workloads/generated/specint-500-pcwatch-20260628-r2/stage_b_summary.json` hit a live kernel Oops/`LINX_EXIT_INIT` at count `2250000011` before any watched user PC fired. Treat these as sensitivity evidence, not the canonical 500 root cause.
  Proposed solution: map the captured `pp_flop` register/frame state back to Perl SV flag/value fields, then isolate the same scalar/range pattern in a smaller Linx-native Perl or C smoke. Compare compiler codegen for scalar IV/NV flag handling before changing SPEC packaging. Keep using BPC heartbeat to distinguish this from QEMU deadlock.

- [x] ID: SPEC-M05-FD-502 `502.gcc_r` must read `200.c` correctly.
  Resolution: the prior `cpugcc_r_base.mytest-m64: fatal error: 200.c: Bad file number` stop was traced to QEMU skipping a predicated FALL into an adjacent conditional CALL shape incorrectly. The fixed skip target now follows the SETRET return continuation through its direct join block, so the musl `fstat` procfd fallback is not entered with stale arguments.
  Evidence: `workloads/generated/specint-502-fstat-argdump-20260628-r2/502_gcc_r/run_001/qemu.log` shows `newfstatat(3, "", stat=0x3ffffff758, AT_EMPTY_PATH) -> 0`, and `LINX_SYSCALL_ARGDUMP` decodes with `st_mode=0x81a4` at stat offset 16. `workloads/generated/specint-502-fstat-syscall-after-call-skip-body-20260628-r1/502_gcc_r/run_001/qemu.log` showed that skipping only to the call-return body still took the stale fallback path. `workloads/generated/specint-502-after-call-skip-join-20260628-r1/stage_b_summary.json` no longer reports `Bad file number`; it reaches a later user trap.
  Follow-up: track the remaining `502.gcc_r` failure under `SPEC-M05-MALLOC-502`.

- [ ] ID: SPEC-M05-MALLOC-502 `502.gcc_r` must survive the post-fstat allocator path.
  Current blocker: after the predicated CALL skip fix, `502.gcc_r` traps in userspace with `addr=0x10`, `tpc=0x1556074e88`, `bpc=0x1556074e80`, `orig_tpc=0x1556074b24`, and no `Bad file number` diagnostic. The allocator corruption is now explained by overlapping heap ranges: musl oldmalloc is the victim, not the current owner.
  Evidence: `workloads/generated/specint-502-after-call-skip-join-20260628-r1/stage_b_summary.json` and `workloads/generated/specint-train-all-20260628-call-skip-join-r1/train-all/initramfs/stage_b_summary.json` classify the benchmark as `user-trap`. With the static PIE slide `0x1515555000`, runtime `0x1556074e88` maps to static `0x40b1fe88` in musl oldmalloc `unbin`, at `c.sdi t#1, [u#1, 16]`. The targeted PC-watch run `workloads/generated/specint-502-alloc-pcwatch-match-a2-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` captures hit `809` immediately before the trap: `a2=0x1556276030`, chunk words `[2]=0x1556273fe0` and `[3]=0`, so oldmalloc is unlinking a bad free-list entry.
  New evidence: `workloads/generated/specint-502-free-overlap-memtrace-context-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` uses `LINX_MEM_TRACE_ACR=2` plus `LINX_MEM_TRACE_CONTEXT=1` to prove the overlapping free chunks share one user address space. It shows oldmalloc first splitting/binning `0x1556276010`, then splitting/binning `0x1556276030`, then allocating payload at `0x1556276020` while `0x1556276030` remains linked as a free chunk. `workloads/generated/specint-502-brk-syscall-trace-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` shows `brk(0x1556273000) -> 0x1556273000`, later failed growths such as `brk(0x1556277000) -> 0x1556273000`, and the final trap. `workloads/generated/specint-502-mmap-syscall-trace-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` shows the fallback anonymous `mmap(0, 0x1ba000, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) -> 0x1556273000`, matching the stalled brk frontier. A rejected one-page kernel guard in `workloads/generated/specint-502-mmap-guard-kernel-20260628-r2/initramfs/502_gcc_r/run_001/qemu.log` moved that mmap to `0x1556274000`, but the failure moved to `memset` at static `0x40b29e4c` with `a0=0x1556273000` and `a2=0x1800`. The latest list-dump trace `workloads/generated/specint-502-alloc-pcwatch-dump-regs-20260628-r1/initramfs/502_gcc_r/run_001/qemu.log` proves the source of the overlap: oldmalloc trims/bin-chunks both `a0=0x1556272ff0` and `a0=0x1556273010`, producing overlapping free chunks at `0x1556276010` and `0x1556276030`. After allocation from `0x1556276010` returns payload `0x1556276020`, GCC's normal GGC writes at `0x15559361c8..0x15559361e6` overwrite the stale `0x1556276030` free-list node; the final `unbin` then sees chunk words `[0]=0x1000 [1]=0x1556277000 [2]=0x1556273fe0 [3]=0`.
  Proposed solution: keep this out of the fd/stat-copyout lane and do not revive the one-page mmap guard as-is. The next fix should separate ordinary anonymous mmap placement from brk-frontier heap-extension mmap: normal large mappings must not land exactly at the current brk frontier while oldmalloc still treats a later same-address anonymous mapping as contiguous heap growth. Candidate fixes are a Linx kernel mmap base/window policy that keeps non-heap anonymous mappings away from `mm->brk`, or a Linx oldmalloc workaround that hints large direct mmaps outside the heap-extension window. Preserve the ability for oldmalloc's fallback heap mmap to extend at `end` when brk growth is exhausted, otherwise the symptom moves to an unmapped memset near `0x1556273000`.

- [ ] ID: SPEC-M05-LIVE-SLOW The live slow train workloads need QEMU speedups or longer diagnostic budgets.
  Current blockers: `505.mcf_r`, `525.x264_r`, `531.deepsjeng_r`, and `557.xz_r` timed out at the 180s train-all diagnostic budget, but QEMU heartbeat counts and BPCs continued to advance and `stalled=false`.
  Evidence:
  - `505.mcf_r`: last heartbeat count `34900000001`, BPC `0x155555c430`, recent unique sites `7`, `progress=site-change`
  - `525.x264_r`: last heartbeat count `20800000000`, BPC `0xffffffff800019bc`, recent unique sites `4`, `progress=site-change`
  - `531.deepsjeng_r`: last heartbeat count `30850000002`, BPC `0x1555560764`, recent unique sites `8`, `progress=site-change`
  - `557.xz_r`: last heartbeat count `30550000006`, BPC `0x155558d612`, recent unique sites `5`, `progress=site-change`
  Note: `523.xalancbmk_r` and `541.leela_r` are current user traps, and should be handled under correctness first.
  Proposed solution: profile with heartbeat off or very coarse; target page-local BSTART decode caching, TB chaining, template/queue fast helpers, and removal of helper probes from hot paths. Current samples are under `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/profile/`.

- [ ] ID: SPEC-M05-USERTRAP-502-541 Deterministic userspace traps must be split from live-slow work.
  Current blockers:
  - `502.gcc_r`: trap `addr=0x305910060a11b059`, user `tpc=0x15559baa04`, `bpc=0x15559ba9fc`.
  - `520.omnetpp_r`: null trap at `tpc=0xeaea2`, `bpc=0xeae90`.
  - `523.xalancbmk_r`: stack-edge trap at `addr=0x3feffffff8`, user `tpc=0x1555a6306a`, `bpc=0x1555a6306a`.
  - `541.leela_r`: stack-edge trap at `addr=0x3feffffff8`, user `tpc=0x1555623796`, `bpc=0x1555623796`.
  Evidence: `workloads/generated/specint-train-all-20260629-pcwatch-offsets-r1/train-all/initramfs/stage_b_summary.json` and per-benchmark qemu logs. Older focused 505 evidence in `workloads/generated/specint-505-final-faultregs-20260628-r1/initramfs/505_mcf_r/run_001/qemu.log` remains historical unless the latest live-timeout run reproduces that trap.
  Proposed solution: rerun 502/520/523/541 focused with `LINX_FAULT_TRACE=1 LINX_FAULT_TRACE_REGS=1`, `LINX_CALL_TRACE_RING=1`, `LINX_DEBUG_PC_WATCH_REGS=1`, and `LINX_DEBUG_PC_WATCH_DUMP_CODE_BYTES=16` around symbolized PCs. Inspect compiler/ABI/QEMU branch-target state and earlier pointer/list corruption before treating any of these as throughput issues.

- [x] ID: SPEC-M05-OLDMALLOC-CPP Early Linx oldmalloc no longer rounds heap growth to zero before libc init.
  Resolution: Linx oldmalloc now falls back to a compile-time page size when `libc.page_size` has not been initialized yet.
  Evidence: `avs/qemu/out/musl-static-oldmalloc-page-20260628/summary.json` passes focused static musl smoke, and `workloads/generated/specint-cxx-after-oldmalloc-20260628/run/initramfs/520_omnetpp_r/run_001/qemu.log` plus `workloads/generated/specint-cxx-after-oldmalloc-20260628/run/initramfs/523_xalancbmk_r/run_001/qemu.log` show first `brk` growth to the next page (`0x27c000` and `0x4f7000`) instead of the earlier no-op `brk(current)`.
  Follow-up: this fixed the allocator symptom only; 520/523 still trap later in C++ runtime or application code.

- [x] ID: SPEC-M05-CPP-STARTUP C++ static SPEC executables enter through musl `_start`, not `main`.
  Resolution: the forced-static C++ wrapper links musl startup objects and C++ runtime archives without `-e main`; the build manifest rejects forced-static images whose ELF entry is not `_start`.
  Evidence: `workloads/generated/specint-cxx-startup-fix-20260628/build_manifest.json` records `static_entry_ok=true` for focused `523.xalancbmk_r` and `541.leela_r`; the current train-all run no longer traps in `__linx_get_tp`/iostream startup for those two benchmarks.
  Follow-up: keep `tools/build_linx_llvm_cpp_runtimes.sh --profile spec --mode phase-b` as a prerequisite after any phase-b musl rebuild.

- [ ] ID: SPEC-M05-CPP-RUNTIME C++ train workloads must finish after startup.
  Current blockers:
  - `520.omnetpp_r`: trap at `addr=0`, `tpc=0xeaea2`, `bpc=0xeae90`; symbolized earlier to `sectionbasedconfig.cc` after `__stdio_read`.
  - `523.xalancbmk_r`: live timeout at 180s after stack-limit fix, TP nonzero.
  - `541.leela_r`: live timeout at 180s after stack-limit fix, TP nonzero.
  Evidence: `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/stage_b_summary.json`, `workloads/generated/specint-cxx-stacklimit-20260628/qemu-focused/qemu_matrix_summary.json`, and the focused register-trace run under `workloads/generated/specint-cxx-after-oldmalloc-20260628/run/initramfs/`.
  Proposed solution: continue `520` as a C++ object/callback correctness trap, and symbolize the `523`/`541` Oops breadcrumbs before treating those runs as pure throughput/profiling cases.

- [x] ID: SPEC-M05-PANIC-525 `525.x264_r` must boot far enough to execute userspace.
  Resolution: the latest rebuilt-QEMU train-all run no longer reproduces the early `LINX_PANIC`; it reaches live execution and times out at the 180s diagnostic budget with BPC progress.
  Evidence: `workloads/generated/specint-train-all-20260628-qemu-dump-regs-r1/train-all/initramfs/525_x264_r/run_001/qemu.log` records `live-timeout`, count `24050000000`, BPC `0xffffffff803e8f46`, recent unique sites `4`, and `stalled=false`. Older runs under `workloads/generated/specint-train-all-20260628-call-skip-join-r1/`, `workloads/generated/specint-train-all-20260628-heartbeat-code-r1/`, `workloads/generated/specint-train-all-20260628-liveness-v2/`, and `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/` are retained as historical panic evidence if the regression returns.
  Follow-up: current 525 ownership is `SPEC-M05-LIVE-SLOW`; reproduce the prior panic only if the latest train-all loop regresses back to `kernel-panic`.

- [ ] ID: SPEC-M05-SHARED-RUNTIME Shared SPEC executables must match the static gate behavior.
  Current blocker: shared phase-b executables all fail quickly in the all-train diagnostic run; even `999.specrand_ir` traps after the rebuild.
  Evidence: `workloads/generated/specint-train-all-20260628-after-kstat/specint_fast_gate_summary.json` and `workloads/generated/specint-train-all-20260628-after-kstat/train-all/qemu_matrix_summary.json`.
  Proposed solution: keep static phase-b as the current correctness gate, and use the shared run only as a libc/loader diagnostic until musl shared startup, `kstat`, and C++ runtime packaging are validated by dedicated static/shared smoke gates.

## Live Blockers (2026-05-21)

- [ ] BLOCK-SPEC-FG-001 Fast SPECint gate must run `test`/`train` before promotion.
  Command: `python3 tools/bringup/run_specint_fast_gate.py --profile pr --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 --qemu "${QEMU:-$PWD/emulator/qemu/build-linx/qemu-system-linx64}" --sysroot "${WORKLOAD_SYSROOT:-$PWD/out/libc/musl/install/phase-b}" --out-dir workloads/generated/specint-fast-gate --append-extra "${SPEC_APPEND_EXTRA:-norandmaps}" --guest-heartbeat-sec "${SPEC_GUEST_HEARTBEAT_SEC:-60}"`
  Done means: `test-smoke` and `train-smoke` emit `qemu_matrix_summary.json` artifacts and the aggregate `specint_fast_gate_summary.json`.
  Rationale: this keeps cheap SPECint regressions visible and prevents `505.mcf_r` or `531.deepsjeng_r` stress workloads from hiding faster `test`/`train` signal.
  Policy: smoke suites are the cheap `999.specrand_ir` sentinels; `531.deepsjeng_r` belongs to nightly `test-cpu-stress`/`train-cpu-stress`, and `505.mcf_r` belongs to nightly VM stress.

- [x] BLOCK-SPEC-A-001 Keep the canonical Stage-A matrix command runnable from the superproject.
  Command: `QEMU=/tmp/linx-qemu-clean-build/qemu-system-linx64 python3 tools/spec2017/run_stage_qemu_matrix.py --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 --stage a --input-set test --strict --out-dir workloads/generated/spec_stage_a_wrapper_verify_env`
  Resolution: `tools/spec2017/run_stage_qemu_matrix.py` now accepts `--qemu` and defaults from `QEMU` in the environment, then forwards that path to `run_int_rate_qemu.py`.
  Evidence: the earlier failure is still captured in `workloads/generated/spec_stage_a_livecheck/qemu_matrix_summary.json`, while the fixed wrapper now successfully stages a transport run under `workloads/generated/spec_stage_a_wrapper_verify_env/9p/999_specrand_ir/run_001/`.

- [ ] BLOCK-SPEC-A-002 `999.specrand_ir` must complete under both Stage-A transports.
  Command: `python3 tools/spec2017/run_int_rate_qemu.py --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 --stage a --transport <9p|initramfs> --input-set test --sysroot out/libc/musl/install/phase-c --qemu /tmp/linx-qemu-clean-build/qemu-system-linx64 --out-dir workloads/generated/spec_stage_a_livecheck_direct/<transport>`
  Blocker: the original shared-runtime route times out on both transports, and the narrowed static fallback still stalls before any guest-visible output. This is now evidence of a broader firmwareless Linux initramfs/userspace-entry blocker, not just a benchmark-local runtime issue.
  Evidence:
  - shared route: `workloads/generated/spec_stage_a_livecheck_direct/9p/stage_a_summary.json`, `.../initramfs/stage_a_summary.json`
  - static fallback: `workloads/generated/spec_stage_a_phaseb_static_999/stage_a_summary.json` (`guest_shared_runtime=false`, `stalled=true`, zero-byte `qemu.log`)
  - libc control lane: `avs/qemu/out/musl-smoke-spec-debug3/summary.json` (`hello_static_runtime_timeout`)
  - no-libc control lane: `kernel/linux/tools/linxisa/initramfs/smoke.py` now also fails against both dirty and sanitized local QEMU builds, so the blocker is below SPEC userspace logic.

- [ ] BLOCK-SPEC-A-003 `505.mcf_r` must complete under both Stage-A transports.
  Command: same as `BLOCK-SPEC-A-002`.
  Blocker: both transports hit the full 240-second guest timeout with no benchmark output files (`inp.out`, `mcf.out`) produced.
  Evidence: `workloads/generated/spec_stage_a_livecheck_direct/9p/stage_a_summary.json`, `.../initramfs/stage_a_summary.json`, and missing-output specdiff logs `.../505_mcf_r_specdiff_1.log` / `..._2.log`.

- [ ] BLOCK-SPEC-A-004 `531.deepsjeng_r` must complete under both Stage-A transports.
  Command: same as `BLOCK-SPEC-A-002`.
  Blocker: both transports hit the full 240-second guest timeout with no benchmark output file (`test.out`) produced.
  Evidence: `workloads/generated/spec_stage_a_livecheck_direct/9p/stage_a_summary.json`, `.../initramfs/stage_a_summary.json`, and missing-output specdiff log `.../531_deepsjeng_r_specdiff_1.log`.

- [ ] BLOCK-SPEC-A-005 The Stage-A subset must reach output generation before specdiff.
  Done means: `rand.24239.out`, `inp.out`, `mcf.out`, and `test.out` exist in the Linx run directories before specdiff executes.
  Blocker: all current Stage-A failures are pre-output guest runtime stalls, not specdiff mismatches after partial progress, and the same silent behavior now reproduces with the static hello control lane.
  Evidence: every current specdiff log reports `Can't open input file ... No such file or directory`.

- [ ] BLOCK-SPEC-A-006 Reconcile stale checklist/docs that still describe `531.deepsjeng_r` as first blocked by missing shared musl.
  Done means: SPEC bring-up docs reflect the current May 21, 2026 stop path.
  Blocker: the stop path has changed twice in one day: earlier shared `phase-c` artifacts were present, then the install tree disappeared, `phase-b` had to be repaired, and the static fallback still hit the same silent runtime stall. The docs need to stop treating the problem as only "`531.deepsjeng_r` needs `libc.so`".
  Evidence: `out/libc/musl/logs/phase-b-summary.txt`, `workloads/generated/spec_stage_a_phaseb_static_999/stage_a_summary.json`, and `avs/qemu/out/musl-smoke-spec-debug3/summary.json`.

- [x] ID: SPEC-M01 Control path ready.
  Canonical plan: `docs/bringup/SPEC_WORKLOAD_PLAN.md`
  Done means: the canonical matrix command is runnable from the superproject, forwards the active QEMU path, and creates per-transport run staging.
  Status: ✅ RESOLVED (2026-05-21) - `run_stage_qemu_matrix.py` now forwards `QEMU=...` / `--qemu ...` to the transport runner.

- [ ] ID: SPEC-M02 Firmwareless Linux userspace entry.
  Canonical plan: `docs/bringup/SPEC_WORKLOAD_PLAN.md`
  Done means: a trivial static initramfs userspace payload emits guest-visible start/pass markers under the same firmwareless Linux/QEMU boot path that SPEC uses.
  Status: ❌ CURRENT FIRST RUNTIME BLOCKER (2026-05-22) - both the corrected static hello control lane and the repo's own no-libc initramfs smoke fail under firmwareless Linux+initramfs boot, so the next runtime blocker is the broader Linux userspace-entry path rather than SPEC harness logic.

- [ ] ID: SPEC-M03 Bringup subset output generation.
  Bringup subset: `spec_policy.bringup_subset`
  Done means: the bringup subset produces its expected output files before specdiff runs.
  Status: ❌ BLOCKED BY SPEC-M02 (2026-05-21) - shared and static narrowed runs still fail before output generation.

- [ ] ID: SPEC-M04 Hosted shared-runtime restoration.
  Command: `MODE=phase-c bash tools/spec2017/build_int_rate_linx.sh --build-runtimes`
  Done means: the shared musl route is restored and dynamic SPEC benches can run against a valid `phase-c` sysroot.
  Status: ❌ OPEN (2026-05-21) - `phase-c` is not the current closure baseline; `phase-b` was repaired first and the shared-runtime path still needs canonical rebuild/revalidation.

- [ ] ID: SPEC-M05 Bringup subset closure.
  Canonical command: `python3 tools/bringup/run_specint_fast_gate.py --profile pr --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 --qemu "${QEMU:-$PWD/emulator/qemu/build-linx/qemu-system-linx64}" --sysroot "${WORKLOAD_SYSROOT:-$PWD/out/libc/musl/install/phase-b}" --out-dir workloads/generated/specint-fast-gate --append-extra "${SPEC_APPEND_EXTRA:-norandmaps}" --guest-heartbeat-sec "${SPEC_GUEST_HEARTBEAT_SEC:-60}"`
  Done means: the fast `test`/`train` suites pass qemu + specdiff/hash checks and aggregate summary reports `ok=true`.
  Status: ❌ BLOCKED BY SPEC-M02 / SPEC-M03 (2026-05-21) - transport summaries still show `ok=false` for every bringup-subset bench.

- [ ] ID: SPEC-M06 Promotion-set closure and xcheck readiness.
  Promotion set: `spec_policy.promotion_required`
  Done means: the promotion set passes the promoted transport policy, phase-b static image prep is reproducible, and LinxCore xcheck promotion is actionable.
  Status: ⚠️ NOT STARTED (2026-05-21) - blocked behind SPEC-M02 through SPEC-M05.

- [ ] ID: SPEC-P01 Fortran exclusion policy.
  Done means: `548.exchange2_r` stays explicitly excluded from Linx intrate scope until the project intentionally expands to Fortran/runtime support.
  Status: ✅ POLICY ACTIVE (2026-05-21)
