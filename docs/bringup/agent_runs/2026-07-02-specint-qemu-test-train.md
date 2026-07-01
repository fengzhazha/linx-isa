# SPECint QEMU test/train bring-up, 2026-07-02

## Scope

This run used the all-SPECint fast gate with `test` and `train` input sets on the Linx QEMU Linux path.

- Root before this log commit: `06b5f45f175a60fbe1a183d392b76c36e765099d`
- LLVM: `57fa07afb3d1d6e7565e692c74ee7a910d8e10f7`
- QEMU: `5cfb672a711bb2172bfe7de6c6b7bd1bdb47e902`
- QEMU version: `QEMU emulator version 10.2.50 (v10.2.0-989-g5cfb672a711)`
- Kernel: `kernel/linux/build-linx-fixed/vmlinux`
- Sysroot: `out/libc/musl/install/phase-b`
- Artifact root: `workloads/generated/specint-test-train-all-after-blockify-20260702-r2`

Command shape:

```bash
SPECINT_TEST_ALL_TIMEOUT=240 SPECINT_TRAIN_ALL_TIMEOUT=360 \
SPEC_GUEST_HEARTBEAT_SEC=0 SPEC_QEMU_HEARTBEAT_INTERVAL=1000000000 \
SPEC_NO_PROGRESS_TIMEOUT=120 LINX_QEMU_HEARTBEAT_SAME_SITE_WARN=4 \
python3 tools/bringup/run_specint_fast_gate.py \
  --profile test-train \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --sysroot out/libc/musl/install/phase-b \
  --out-dir workloads/generated/specint-test-train-all-after-blockify-20260702-r2 \
  --append-extra norandmaps --heartbeat-sec 30 \
  --qemu-heartbeat-interval 1000000000 --guest-heartbeat-sec 0 \
  --no-progress-timeout 120 --stack-limit 2G --transports initramfs \
  --continue-on-fail --symbolize-heartbeat --dump-prefix-bytes 512
```

## Gate results

The run is red overall. The heartbeat/BPC switch separated live execution from hard failures: live-timeout rows continued to emit `LINX_HEARTBEAT ... bpc=... progress=site-change`, while `525.x264_r` stopped before init with no progress.

`test-all` summary:

| Bench | Runs | Pass | Failure | Evidence |
|---|---:|---:|---|---|
| `500.perlbench_r` | 2 | 1 | run 2 `spec-wrapper-fail` | child SIGSEGV after kernel Oops, `trapno=0xc000000002000001` |
| `502.gcc_r` | 1 | 1 | none | generated `.s` hash matched |
| `505.mcf_r` | 1 | 0 | `live-timeout` | BPC/site progress through 240 seconds |
| `520.omnetpp_r` | 1 | 0 | `spec-wrapper-fail` | child SIGKILL, `sig=9` |
| `523.xalancbmk_r` | 1 | 0 | `spec-wrapper-fail` | child SIGKILL, `sig=9` |
| `525.x264_r` | 1 | 0 | `kernel-panic` | `VFS: Unable to mount root fs`, initramfs is about 1.6 GB |
| `531.deepsjeng_r` | 1 | 0 | `live-timeout` | BPC/site progress through 240 seconds |
| `541.leela_r` | 1 | 0 | `spec-wrapper-fail` | child SIGKILL, `sig=9` |
| `557.xz_r` | 12 | 12 | none | all output hashes matched |
| `999.specrand_ir` | 1 | 1 | none | output hash matched |

`train-all` summary:

| Bench | Runs | Pass | Failure | Evidence |
|---|---:|---:|---|---|
| `500.perlbench_r` | 3 | 3 | none after runner fix | all three output hashes matched; historical JSON marked specdiff rc=2 |
| `502.gcc_r` | 1 | 0 | `spec-wrapper-fail` | child exit code 4; benchmark internal compiler-error message in stderr |
| `505.mcf_r` | 1 | 0 | `live-timeout` | BPC/site progress through 360 seconds |
| `520.omnetpp_r` | 1 | 0 | `spec-wrapper-fail` | child SIGKILL, `sig=9` |
| `523.xalancbmk_r` | 1 | 0 | `spec-wrapper-fail` | child SIGKILL, `sig=9` |
| `525.x264_r` | 1 | 0 | `kernel-panic` | `VFS: Unable to mount root fs`, initramfs is about 1.6 GB |
| `531.deepsjeng_r` | 1 | 0 | `live-timeout` | BPC/site progress through 360 seconds |
| `541.leela_r` | 1 | 0 | `spec-wrapper-fail` | child SIGKILL, `sig=9` |
| `557.xz_r` | 1 | 0 | `live-timeout` | BPC/site progress through 360 seconds; transient `LINX_HEARTBEAT_STALL` recovered to site changes |
| `999.specrand_ir` | 1 | 1 | none | output hash matched |

Machine-readable summaries:

- `workloads/generated/specint-test-train-all-after-blockify-20260702-r2/test-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-test-train-all-after-blockify-20260702-r2/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-test-train-all-after-blockify-20260702-r2/specint_fast_gate_summary.json`

## Follow-up focused diagnostics

`520.omnetpp_r` was rerun with guest heartbeat `/proc` sampling enabled:

- Artifact: `workloads/generated/specint-520-guestdiag-20260702-r1/test/qemu_matrix_summary.json`
- Result: `live-timeout`, not a reproduced child SIGKILL.
- Liveness: QEMU heartbeat remained running with site progress through 240 seconds; last BPC was `0xffffffff800091dc`.
- Kernel symbols at recent heartbeat sites included `vsprintf.c`, `string.c`, `memory.c`, `page_alloc.c`, `printk_ringbuffer.c`, `mmap.c`, and final idle-loop sites.
- Guest memory snapshot at the child heartbeat showed `MemFree: 2040952 kB`, `MemAvailable: 2041044 kB`, and `oom_kill 0`.
- Interpretation: this reproduction is a throughput/live-progress failure, not guest OOM. The earlier SIGKILL rows still need per-row reproduction with guest heartbeat because the failure mode is not stable across focused reruns.

Wrapper compile/run smoke after the diagnostics change:

- Artifact: `workloads/generated/specint-999-guestdiag-compile-20260702-r1/test/qemu_matrix_summary.json`
- Result: `999.specrand_ir` test/initramfs passed in 19.328 seconds under strict hash validation.

Additional focused diagnostics:

- `workloads/generated/specint-523-541-guestdiag-20260702-r1/test/qemu_matrix_summary.json`
  reran `523.xalancbmk_r` and `541.leela_r` with guest heartbeat sampling.
- `523.xalancbmk_r` first rerun: `user-trap`, not SIGKILL. Runtime BPC
  `0x15559efe1a` maps to ELF `0x404afe1a`, `.LBB24_28` in `locale.cpp`, at
  the libc++ `num_get` indirect-call path. Guest memory snapshot showed
  `MemAvailable: 1975216 kB` and `oom_kill 0`.
- `workloads/generated/specint-523-faultregs-20260702-r1/test/qemu_matrix_summary.json`
  reran `523.xalancbmk_r` with QEMU fault-register tracing enabled through the
  SPEC runner. The switch worked and emitted `LINX_FAULT_TRACE` plus
  `LINX_FAULT_REGS`, but this rerun did not reproduce the user trap; it became
  a `live-timeout` with BPC/site progress through 180 seconds.
- `workloads/generated/specint-541-oomclass-20260702-r1/test/qemu_matrix_summary.json`
  reran `541.leela_r` after the classifier update. It now reports
  `spec-child-sigkill-oom`; guest memory fell from about 2046404 kB available
  to 16348 kB available before `oom_kill` incremented to 1, then wait status
  reported `signaled=1 sig=9`.
- `workloads/generated/specint-541-mem4096-20260702-r1/test/qemu_matrix_summary.json`
  reran `541.leela_r` with 4096 MiB and `--stack-limit 2G`, removing the
  2 GiB OOM pressure. The old executable then failed with a user trap at
  `addr=0x3f7ffffff8`, `sp=0x3f80000000`, and `tpc=0x15556253d6`. Correcting
  the ET_DYN base maps this to ELF `0x400d03d6`, `__atomic_load_1`; disassembly
  showed that the compiler-rt specialized helper called itself recursively.
- `compiler/llvm/compiler-rt/lib/builtins/atomic.c` now has a Linx-only guard
  that keeps compiler-rt atomic builtins away from `__c11_atomic_*`, because
  the current Linx backend lowers those C11 atomics back to the same public
  `__atomic_*` symbols. This is a bring-up fallback until native atomic
  lowering exists.
- Rebuild evidence:
  - `MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh` passed and
    refreshed `out/libc/musl/logs/phase-b-summary.txt`.
  - `bash tools/build_linx_llvm_cpp_runtimes.sh --profile spec --mode phase-b`
    passed and restored the spec-profile C++ runtime overlay into the phase-b
    sysroot.
  - `workloads/generated/specint-build-541-atomicfix-20260702-r1/build_manifest.json`
    records a successful static phase-b rebuild of `541.leela_r`.
  - `out/libc/musl/runtime/phase-b/obj/atomic.c.o` and the relinked Leela
    executable both show direct `lbui/lhui/lwi/ldi` bodies for
    `__atomic_load_{1,2,4,8}` rather than recursive calls.
- `workloads/generated/specint-541-atomicfix-20260702-r1/test/qemu_matrix_summary.json`
  reran the fixed `541.leela_r` binary with the same 4096 MiB /
  `--stack-limit 2G` policy. The row no longer traps, panics, or OOMs; it
  becomes `live-timeout` at 420 seconds with heartbeat site progress,
  count `45000000002`, recent count delta `6999999998`, seven recent unique
  BPC sites, `oom_kill 0`, and a small stack (`VmStk: 316 kB`).
- `workloads/generated/specint-541-atomicfix-long-20260702-r1/test/qemu_matrix_summary.json`
  reran the same fixed binary with a 1200 second cap. It now fails earlier with
  a fresh user trap at `addr=0x0`, `tpc=0x155561559c`, `bpc=0x1555615598`,
  `orig_tpc=0x15556171e6`, and `ra=0x15556152ca`. Using the ET_DYN base
  `0x1551555000`, the trap maps to ELF `0x400c059c` in musl mallocng
  `get_meta`, specifically the `a_crash()` path for
  `assert(area->check == ctx.secret)`. Guest memory was not pressured
  (`oom_kill 0`), so this supersedes the 420 second live-timeout classification
  for `541`: atomic recursion is closed, and the next blocker is allocator
  metadata corruption, codegen, or mmap/free-path correctness.

## Tool fixes in this loop

- Fixed the GCC test input verifier to compare the generated `.s` output instead of a nonexistent `.out`.
- Added an opt-in printf self-test to the SPEC init wrapper for ABI debug.
- Fixed a false-red path where exact strict host hashes were overwritten by host `specdiff` rc=2. The train `500.perlbench_r` run artifact predates this fix, so its JSON still shows `specdiff-mismatch` even though every output hash matches.
- Added guest heartbeat process/memory sampling for initramfs child runs: `/proc/$pid/status`, `/proc/meminfo`, `/proc/vmstat`, and optional `/proc/pressure/memory`.
- Split child SIGKILL/SIGSEGV rows into explicit JSON failure classes (`spec-child-sigkill`, `spec-child-sigsegv`) instead of generic `spec-wrapper-fail`.
- Split SIGKILL plus observed guest `oom_kill` into `spec-child-sigkill-oom`.
- Added runner/matrix switches for QEMU's existing fault-register tracing:
  `--qemu-fault-trace-regs` and `--qemu-fault-trace-limit`.
- Added runner/matrix pass-through for focused QEMU fault-trace filters:
  `--qemu-fault-trace`, `--qemu-fault-trace-pc[-lo|-hi]`,
  `--qemu-fault-trace-addr[-lo|-hi]`, `--qemu-fault-trace-count[-lo|-hi]`,
  and `--qemu-fault-trace-trapnum`.

## Profile observations

Profiles:

- `workloads/generated/specint-test-train-all-after-blockify-20260702-r2/profiles/qemu-train-active.sample.txt`
- `workloads/generated/specint-test-train-all-after-blockify-20260702-r2/profiles/qemu-train-520-active.sample.txt`

Hot paths seen in both profiles:

- `helper_linx_template_step`
- `helper_linx_check_bstart_target`
- `probe_access_flags` and `mmu_lookup` under BSTART legality checks
- `linx_trace_wb` and `linx_call_trace_emit`, even in non-trace SPEC runs

## Proposed next loops

1. QEMU speed: cache BSTART legality per TB or per guest code page and avoid repeated helper-side `probe_access_flags` for the same target. This is the hottest repeated path in both profiles.
2. QEMU speed: split `helper_linx_template_step` into fast paths for common non-template/non-trace execution and keep trace hooks fully disabled unless an explicit trace switch is set.
3. QEMU debug: add an exit counter summary with TB count, dynamic instruction count, BSTART checks, BSTART cache hits/misses, template helper calls, MMU probes, trace hook calls, heartbeat stall count, and last BPC.
4. SPEC gate: classify `live-timeout` as a performance failure distinct from correctness failures. Keep the correctness gate on hash-matching rows, and run timeout rows in a separate throughput budget.
5. `525.x264_r`: do not use initramfs transport for full x264 inputs. The generated cpio is about 1.6 GB and panics before init. Use 9p/virtio payload transport or split input staging.
6. `502.gcc_r`: treat train as a compiler/codegen bug first. It exits with code 4 and reports a benchmark internal compiler error. Rebuild at lower optimization or bisect Linx LLVM codegen around GCC tree-SSA paths.
7. SIGKILL rows are now split by evidence. `541.leela_r` is real guest OOM at
   2 GiB, but at 4 GiB the old user trap was compiler-rt atomic recursion and
   is now fixed. The next `541` blocker is the later mallocng `get_meta`
   null-address `a_crash`; rerun with QEMU fault-register filters around
   `0x1555615580..0x15556155b0` and add a focused metadata dump before changing
   mallocng, compiler, or QEMU. Prior `520` did not reproduce SIGKILL and
   showed `oom_kill 0`; keep it in live-timeout/performance triage unless a
   fresh run proves otherwise. `523.xalancbmk_r` is unstable between user-trap
   and live-timeout; rerun with fault trace filters around the user BPC if the
   trap reproduces.
8. `500.perlbench_r` test run 2: investigate kernel Oops/SIGSEGV separately from train. The test row traps before hash verification; train hashes all match.

## Verification

- `PYTHONPATH=tools/spec2017 python3 -m unittest -q tools.spec2017.test_run_int_rate_qemu tools.spec2017.test_run_stage_qemu_matrix`
- `git diff --check -- tools/spec2017/run_int_rate_qemu.py tools/spec2017/test_run_int_rate_qemu.py`
- `python3 -m py_compile run_int_rate_qemu.py test_run_int_rate_qemu.py` from `tools/spec2017`
- `python3 -m unittest test_run_int_rate_qemu.py` from `tools/spec2017`
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 520.omnetpp_r --input-set test --transports initramfs --guest-heartbeat-sec 10 --timeout 240` (expected red, classified `live-timeout`)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 999.specrand_ir --input-set test --transports initramfs --guest-heartbeat-sec 10 --timeout 180` (passed)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 523.xalancbmk_r --bench 541.leela_r --input-set test --transports initramfs --guest-heartbeat-sec 10 --timeout 240` (expected red, classified `523` as `user-trap`, `541` as SIGKILL before OOM classifier)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 523.xalancbmk_r --input-set test --transports initramfs --guest-heartbeat-sec 10 --qemu-fault-trace-regs --timeout 180` (expected red, verified QEMU fault-reg switch; rerun classified `live-timeout`)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 541.leela_r --input-set test --transports initramfs --guest-heartbeat-sec 10 --timeout 240` (expected red, classified `spec-child-sigkill-oom`)
- `MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh` (passed after Linx compiler-rt atomic fallback)
- `bash tools/build_linx_llvm_cpp_runtimes.sh --profile spec --mode phase-b` (passed, restored C++ overlay)
- `LINX_SPEC_LINK_MODE=default bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 541.leela_r --emit-manifest workloads/generated/specint-build-541-atomicfix-20260702-r1/build_manifest.json` (passed)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 541.leela_r --memory-mb 4096 --stack-limit 2G --timeout 420` (expected red, old `__atomic_load_1` user trap closed; classified `live-timeout` with heartbeat progress)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 541.leela_r --memory-mb 4096 --stack-limit 2G --timeout 1200` (expected red, old atomic recursion still closed; later mallocng `get_meta` assertion traps at `addr=0`)
- `skill-evolve: update linx-compiler (record compiler-rt/C11 atomic recursion triage and fallback verification)`
