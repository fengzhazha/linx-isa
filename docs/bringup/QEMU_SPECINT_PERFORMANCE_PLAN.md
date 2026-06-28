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
  `LINX_MEM_TRACE_SIZE`, `LINX_MEM_TRACE_ACCESS=load|store|all`,
  `LINX_MEM_TRACE_LIMIT`, and `LINX_MEM_TRACE_PC_LO/HI`.
- `LINX_SYSCALL_TRACE=1` logs Linx hosted syscall entry and ACRE return pairs
  with syscall number, BPC/TPC, arguments, return value, and cstate. Narrow
  with `LINX_SYSCALL_TRACE_NR`, `LINX_SYSCALL_TRACE_LIMIT`, and
  `LINX_SYSCALL_TRACE_PC_LO/HI`.
- `LINX_SYSCALL_TRACE_STRINGS=1` augments syscall tracing with separate
  `LINX_SYSCALL_ARGSTR` records for pathname arguments. Bound reads with
  `LINX_SYSCALL_TRACE_STRING_MAX=<1..255>` so path/fd failures can be
  diagnosed without enabling full memory traces.
- `LINX_SYSCALL_TRACE_REGS=1` prints a `LINX_SYSCALL_REGS` record for each
  traced syscall entry and return with the full Linx GPR file. This is useful
  when return-value clobbering, TLS state, or caller-save handling is suspect.
- `LINX_FAULT_TRACE_REGS=1` prints a `LINX_FAULT_REGS` record after
  `LINX_FAULT_TRACE` reports a synchronous trap, again with the full GPR file.
- `LINX_TRACE_REGS=1` enables both syscall and fault register records.
- `LINX_TP_TRACE=1` records user-to-kernel TP handoff points for service
  requests, synchronous traps, IRQ entry, and ACRE staging. Use
  `LINX_TP_TRACE_LIMIT=<n>` on full SPEC runs.
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

Latest diagnostic rerun after the TP/BPC heartbeat extension, static C++
startup-entry repair, and initramfs launcher stack-limit fix. This is the
current fast train-all loop: all ten SPECint train benchmarks, initramfs
transport, 180s per benchmark, no guest heartbeat, and a QEMU heartbeat every
50M guest instructions.

```bash
python3 tools/spec2017/run_stage_qemu_matrix.py \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --stage b \
  --input-set train \
  --transports initramfs \
  --sysroot out/libc/musl/install/phase-b \
  --timeout 180 \
  --heartbeat-sec 30 \
  --qemu-heartbeat-interval 50000000 \
  --no-progress-timeout 120 \
  --guest-heartbeat-sec 0 \
  --append-extra norandmaps \
  --out-dir workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/run
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
- `workloads/generated/specint-502-syscall-argstr-smoke-20260628/run/initramfs/502_gcc_r/run_001/qemu.log`
- `workloads/generated/specint-502-static-fulltrace-post-gtod-20260628/run/initramfs/502_gcc_r/run_001/qemu.log`
- `avs/qemu/out/musl-time-syscalls-20260628/summary.json`

Result: all ten train-input benchmarks build in the static phase-b gate.
`999.specrand_ir` passes by hash. The other nine train-input benchmarks are
classified by first failing symptom. No benchmark in the current run was marked
`stalled`; every failed run had heartbeat progress, so the failures below are
crash/correctness/throughput stops rather than a global QEMU deadlock. The old
C++ `_start`/TP symptom is removed: `523.xalancbmk_r` and `541.leela_r` now
enter through musl `_start` with nonzero TP and fail only by live timeout after
the launcher raises `RLIMIT_STACK`.

| Benchmark | Result | Evidence | Current classification |
| --- | --- | --- | --- |
| `500.perlbench_r` | fail | `Range iterator outside integer range at lib/Math/BigInt.pm line 2675`; last heartbeat had `progress=site-change`, BPC `0x15556fd9d0` | reaches Perl user code; investigate integer range/codegen/libc conversion state |
| `502.gcc_r` | fail | `cpugcc_r_base.mytest-m64: fatal error: 200.c: Bad file number`; last heartbeat in kernel fd path had `progress=site-change`, BPC `0xffffffff8006ba9c` | static userspace errno/file-state corruption, not currently proven as kernel fd-table failure |
| `505.mcf_r` | user trap | `addr=0x19`, `tpc=0x155555b860`, `bpc=0x155555b85a`; last heartbeat still had `progress=site-change` | deterministic null/small-pointer userspace trap |
| `520.omnetpp_r` | user trap | `addr=0`, `tpc=0xeaea2`, `bpc=0xeae90`; heartbeat was live before the trap | C++ object/callback path after allocator growth succeeds |
| `523.xalancbmk_r` | live timeout at 180s | last heartbeat count `36600000005`, BPC `0xffffffff803dde02`, `progress=same-site`, `stalled=false`, TP nonzero | running too slowly in the 180s diagnostic budget, not the earlier TP/startup trap |
| `525.x264_r` | panic | `LINX_PANIC caller=0xffffffff80001648` | early kernel/initramfs path |
| `531.deepsjeng_r` | user trap | branch target trap with `tpc=0`, `bpc=0`, `bpcn=0x1555576390`; last heartbeat had `progress=site-change` | deterministic indirect-control/target-state userspace trap |
| `541.leela_r` | live timeout at 180s | last heartbeat count `13650000004`, BPC `0xffffffff800091d8`, `progress=site-change`, `stalled=false`, TP nonzero | running too slowly in the 180s diagnostic budget, not the earlier TP/startup trap |
| `557.xz_r` | live timeout at 180s | last heartbeat count `24350000000`, BPC `0xffffffff80110c46`, `progress=site-change`, `stalled=false` | running too slowly, not deadlocked |
| `999.specrand_ir` | pass | `LINX_SPEC_PASS 999.specrand_ir`; FNV-1a `rand.11.out` hash `0x973dcfc2` matches | smoke sentinel closed |

The shared-runtime diagnostic run in
`workloads/generated/specint-train-all-20260628-after-kstat/` currently fails
all ten benchmarks quickly, including `999.specrand_ir`. That route is useful
for loader/libc diagnosis but is not the current SPEC correctness gate. The
static phase-b route is the baseline for benchmark correctness while shared
startup and C++ runtime packaging are being repaired.

The SPEC loop now records bounded failure classes in both
`stage_b_summary.json` and `qemu_matrix_summary.md`. A post-rebuild focused
matrix over `999.specrand_ir` and `541.leela_r` proves the summary plumbing:
`999.specrand_ir` passes, while `541.leela_r` is summarized as `user-trap`.

Proposed next fixes:

1. Keep the QEMU heartbeat disabled by default, but enable it on long train
   runs to distinguish live progress from deadlock. Use BPC/PC churn plus
   `progress` and `same_site` before increasing timeouts.
2. Profile `523.xalancbmk_r`, `541.leela_r`, and `557.xz_r` with heartbeat
   off or at a very coarse interval. These workloads are live but too slow in
   the 180s train-all diagnostic loop; the next QEMU speedups should focus on
   page-local BSTART decode caching, TB-friendly template/queue fast paths,
   and avoiding helper probes in hot branch-validation paths.
3. Continue `500.perlbench_r` from the user-code BigInt stop. The earlier
   kernel Oops is no longer the first stop in this loop. Symbolize the Perl
   failure path, then inspect integer range codegen, libc conversion helpers,
   and call/return ABI only where the symbolized path points.
4. Continue `502.gcc_r` from the post-`gettimeofday` trace. Syscall 169 now
   returns `0`, `200.c` opens as fd 3, fd/procfd status checks succeed, and
   the trace contains no `-EBADF` syscall return. The next target is
   userspace state: symbolize/instrument `cpp_files.c:open_file` and
   `open_file_failed`, then validate static musl errno/TLS and the compiler
   codegen that stores `file->err_no`.
5. Continue deterministic userspace traps separately from throughput work:
   `505.mcf_r` traps at small address `0x19`, `520.omnetpp_r` traps on a null
   object/callback path, and `531.deepsjeng_r` traps through a zero branch
   target state. Use `LINX_FAULT_TRACE_REGS=1` plus symbolization before
   changing QEMU control-flow rules.
6. Reproduce `525.x264_r` with the same initramfs footprint but a tiny payload,
   symbolize `0xffffffff80001648`, and inspect early unpack/page-allocation
   paths before treating it as an x264 userspace failure.
7. Keep `train-all` opt-in through `--profile train`; the PR gate should stay
   on cheap `999.specrand_ir` smoke while stress workloads run in isolated
   nightly or diagnostic lanes.

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
2. Continue from the current `Math::BigInt` user-code failure captured by
   `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/run/`.
   If the older post-oldmalloc `LINX_DIE msg=Oops` reappears, reproduce it
   with `LINX_FAULT_TRACE_REGS=1` and symbolize the kernel stop before
   changing the Perl/runtime path.
3. Keep the v0.56 fixup parser as a prerequisite for all uaccess-heavy SPEC
   work; without it, normal faultable usercopy recovery is misclassified as an
   unhandled kernel page fault.

## Next Speedups

Current train-all live-progress evidence:

- `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/run/initramfs/523_xalancbmk_r/run_001/qemu.log`
  last heartbeat: count `36600000005`, BPC `0xffffffff803dde02`,
  PC `0xffffffff803dde02`, `progress=same-site`, `same_site=3`.
- `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/run/initramfs/541_leela_r/run_001/qemu.log`
  last heartbeat: count `13650000004`, BPC `0xffffffff800091d8`,
  PC `0xffffffff800091f2`, `progress=site-change`.
- `workloads/generated/specint-train-all-20260628-heartbeat-stacklimit/run/initramfs/557_xz_r/run_001/qemu.log`
  last heartbeat: count `24350000000`, BPC `0xffffffff80110c46`,
  PC `0xffffffff80110566`, `progress=site-change`.
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
- The current samples still show visible time in `helper_linx_scalar_read_reg`,
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
