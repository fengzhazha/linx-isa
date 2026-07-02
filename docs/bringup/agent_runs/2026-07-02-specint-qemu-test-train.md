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

The all-row wrapper has since been updated so this old `525.x264_r`
classification is no longer the default all-row gate behavior. `525.x264_r`
stays in `test-all` and `train-all`, but it runs through generated
`test-all-large-9p` / `train-all-large-9p` shards unless `--transports`
explicitly overrides the policy.

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

Focused `525.x264_r` transport diagnostics:

- `workloads/generated/specint-525-9p-current-20260702-r1/test/qemu_matrix_summary.json`
  reran `525.x264_r` test input with 9p transport. It reached userspace and
  classified as `live-timeout` at 360 seconds, count `43000000004`, recent
  delta `7000000000`, eight recent unique BPC sites, no trap, no panic, and
  no 9p mount warning.
- `workloads/generated/specint-525-9p-train-20260702-r1/train/qemu_matrix_summary.json`
  reran `525.x264_r` train input with 9p transport, 4096 MiB, and the same
  `--stack-limit 2G` policy. It classified as `live-timeout` at 480 seconds,
  count `55000000000`, recent delta `6999999998`, eight recent unique BPC
  sites, no trap, no panic, and no 9p mount warning.
- Interpretation: x264 is a QEMU throughput/live-progress row under the proper
  payload transport. The prior `kernel-panic` rows are initramfs transport
  artifacts caused by the about-1.6 GiB generated cpio, not x264 correctness
  failures.

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
- `workloads/generated/specint-541-mallocng-faultregs-20260702-r1/test/qemu_matrix_summary.json`
  reran the mallocng binary with QEMU fault-register filters around
  `0x1555615580..0x15556155b0`; the trap did not reproduce and the row stayed
  live through the 300 second cap.
- `workloads/generated/specint-541-mallocng-pcwatch-ring-20260702-r1/test/qemu_matrix_summary.json`
  tried to capture a late PC-watch ring, but an earlier null-address mallocng
  assert fired first at `tpc=0x1555616858`, count `1082228490`. That runtime PC
  maps to ELF `0x400c1858`, the `a_crash()` path for mallocng `queue()` and
  `assert(!m->next)` in the `alloc_slot()` path.
- `workloads/generated/specint-541-mallocng-queue-meta-20260702-r1/test/qemu_matrix_summary.json`
  narrowed the PC-watch count window around that `queue()` assert, but the
  failure did not reproduce in the 120 second cap. Treat the mallocng asserts
  as nondeterministic metadata corruption until a focused memory trace proves
  whether the owner is libc, codegen, or QEMU/Linux VM behavior.
- `MALLOC_IMPL=oldmalloc MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh`
  rebuilt phase-b musl with oldmalloc, `bash tools/build_linx_llvm_cpp_runtimes.sh
  --profile spec --mode phase-b` refreshed the C++ overlay, and
  `workloads/generated/specint-build-541-oldmalloc-20260702-r1/build_manifest.json`
  records a successful static relink of `541.leela_r`.
- `workloads/generated/specint-541-oldmalloc-20260702-r1/test/qemu_matrix_summary.json`
  reran oldmalloc-linked `541` with 4096 MiB and `--stack-limit 2G`. It stayed
  live through 420 seconds with BPC/site progress, count `45000000008`, recent
  count delta `6999999990`, eight recent unique BPC sites, no trap, no panic,
  and `oom_kill 0`.
- `workloads/generated/specint-541-oldmalloc-long-20260702-r1/test/qemu_matrix_summary.json`
  reran the oldmalloc-linked `541` with a 1200 second cap. It remained a
  heartbeat-backed `live-timeout`: elapsed `1200.376` seconds, count
  `133000000000`, last BPC `0x1555592176`, recent count delta `7000000000`,
  eight recent unique BPC sites, no trap, no panic, and `oom_kill 0`. This does
  not make `541` correct or fast enough, but it cleanly splits the current
  mallocng metadata asserts from the closed compiler-rt atomic recursion.

## Post-perlbench all-train split rerun

Artifact root:

- `workloads/generated/specint-train-split-post-perlbench-20260702-r1`

Version context:

- QEMU: `5cfb672a711b`, `QEMU emulator version 10.2.50 (v10.2.0-989-g5cfb672a711)`
- LLVM: `e4771587a947`
- Kernel: `kernel/linux/build-linx-fixed/vmlinux`
- Sysroot: `out/libc/musl/install/phase-b`

Command shape:

```bash
python3 tools/bringup/run_specint_fast_gate.py \
  --profile train \
  --spec-dir workloads/spec2017/cpu2017v118_x64_gcc12_avx2 \
  --qemu emulator/qemu/build-linx/qemu-system-linx64 \
  --sysroot out/libc/musl/install/phase-b \
  --out-dir workloads/generated/specint-train-split-post-perlbench-20260702-r1 \
  --append-extra norandmaps --heartbeat-sec 30 \
  --qemu-heartbeat-interval 1000000000 \
  --no-progress-timeout 0 --stack-limit 2G \
  --guest-heartbeat-sec 0 --symbolize-heartbeat \
  --continue-on-fail
```

The generated train profile split `525.x264_r` into the large-payload 9p shard
and kept the other nine rows on initramfs. This run was started before the
final classifier/fail-fast patches in this loop, so the raw logs and focused
`502.gcc_r` repro below supersede any stale generic class in the original
matrix JSON.

Current all-train result ledger:

| Bench | Transport | Result | Liveness evidence |
|---|---|---|---|
| `500.perlbench_r` | initramfs | `live-timeout` | first train row now starts at `diffmail`; BPC changed through count `46000000002`, last BPC `0x15556d96a4` |
| `502.gcc_r` | initramfs | `spec-benchmark-internal-error` | focused current-code repro reports the SPEC GCC internal error at `tree-into-ssa.c:942`, child exit code 4 |
| `505.mcf_r` | initramfs | `live-timeout` | BPC changed through count `48000000005`, last BPC `0x155555c4a4` |
| `520.omnetpp_r` | initramfs | `live-timeout` | BPC changed through count `44000000019`, last BPC `0xffffffff800f683a` |
| `523.xalancbmk_r` | initramfs | `live-timeout` | BPC changed through count `44000000000`, last BPC `0xffffffff8006aca2` |
| `525.x264_r` | 9p | `live-timeout` | all four generated train rows timed out with site progress; final row reached count `22000000014`, last BPC `0xffffffff80112032` |
| `531.deepsjeng_r` | initramfs | `live-timeout` | BPC changed through count `46000000023`, last BPC `0x155555b6fa` |
| `541.leela_r` | initramfs | `live-timeout` | BPC changed through count `15000000005`, last BPC `0x155558ee8e` |
| `557.xz_r` | initramfs | `live-timeout` | BPC changed through count `36000000014`, last BPC `0x155558cc70` |
| `999.specrand_ir` | initramfs | pass | strict hash pass, `LINX_SPEC_PASS 999.specrand_ir` |

Machine-readable summaries:

- `workloads/generated/specint-train-split-post-perlbench-20260702-r1/specint_fast_gate_summary.json`
- `workloads/generated/specint-train-split-post-perlbench-20260702-r1/train-all/initramfs/stage_b_summary.json`
- `workloads/generated/specint-train-split-post-perlbench-20260702-r1/train-all-large-9p/9p/stage_b_summary.json`

Focused `502.gcc_r` classifier proof:

- `workloads/generated/specint-502-internal-error-class-20260702-r3/qemu_matrix_summary.json`
- Result: `spec-benchmark-internal-error`
- Evidence: `200.c:63888:3: benchmark internal error: in ?, at tree-into-ssa.c:942; LINX_SPEC_FAIL child-exit; ... code=4`

This repro also closed a runner-reporting bug: QEMU output carries carriage
returns in the SPEC stderr marker block, so the classifier now normalizes QEMU
log bytes before matching `LINX_SPEC_STDERR_BEGIN/END`. Without that
normalization, the raw log contained the internal-error text while JSON stayed
at generic `spec-wrapper-fail`.

Focused `502.gcc_r` conservative-codegen probe:

- `workloads/generated/specint-502-current-argv-20260702-r1/stage_b_summary.json`
  reran train row 1 on the current runner and default 502 binary. It reproduced
  `spec-benchmark-internal-error` at `tree-into-ssa.c:942`, with child exit
  code 4 and exact argv now recorded in both JSON and QEMU log:
  `./cpugcc_r_base.mytest-m64 200.c -O3 -finline-limit=50000 -o 200.opts-O3_-finline-limit_50000.s`.
- `workloads/generated/specint-build-502-conservative-20260702-r1/build_manifest.json`
  rebuilt only `502.gcc_r` as a static phase-b binary with
  `-O0 -fno-vectorize -fno-slp-vectorize -fno-inline -fno-optimize-sibling-calls
  -fno-strict-aliasing -fwrapv -fno-jump-tables`; the source immutability check
  passed.
- `workloads/generated/specint-502-conservative-20260702-r1/stage_b_summary.json`
  reran the same row with a 240 second cap. The internal error did not
  reproduce; the row became `live-timeout`, with heartbeat site progress to
  count `32000000006`, last BPC `0x15559e77aa`, no trap, no panic, and no fail
  marker.
- `workloads/generated/specint-502-conservative-long-20260702-r1/stage_b_summary.json`
  extended the same conservative binary to 600 seconds. It remained
  `live-timeout`, with heartbeat site progress to count `91000000002`, last BPC
  `0x1555fbd61c`, recent count delta `6999999998`, seven recent unique BPC
  sites, no trap, no panic, and no fail marker.

Interpretation: the default 502 binary still has a real codegen-sensitive
misbehavior, but the conservative build turns the immediate benchmark internal
error into a throughput row rather than proving correctness. Keep this as a
compiler/codegen localization probe; do not promote the flag bundle as a
correctness fix until the generated `.s` output reaches strict hash/specdiff
validation. After the probe, `502.gcc_r` was rebuilt back to the default
`-O0 -fno-vectorize -fno-slp-vectorize` flag set; restore evidence is
`workloads/generated/specint-build-502-default-restore-20260702-r1/build_manifest.json`.

Focused `502.gcc_r` flag-bisect follow-up:

- `workloads/generated/specint-build-502-no-jumptables-20260702-r1/build_manifest.json`
  rebuilt 502 with default flags plus `-fno-jump-tables`. The row still
  reproduced `spec-benchmark-internal-error` at `tree-into-ssa.c:942` in
  `workloads/generated/specint-502-no-jumptables-20260702-r1/stage_b_summary.json`
  after `113.397` seconds, count `18000000001`, last BPC `0x1555e5429c`.
- `workloads/generated/specint-build-502-no-inline-20260702-r1/build_manifest.json`
  rebuilt 502 with default flags plus `-fno-inline`. The row still reproduced
  the same internal error in
  `workloads/generated/specint-502-no-inline-20260702-r1/stage_b_summary.json`
  after `145.321` seconds, count `18000000000`.
- `workloads/generated/specint-build-502-semantic-flags-20260702-r1/build_manifest.json`
  rebuilt 502 with default flags plus `-fno-optimize-sibling-calls
  -fno-strict-aliasing -fwrapv`. The row did not reproduce the internal error
  under the 240 second cap and instead classified as `live-timeout` in
  `workloads/generated/specint-502-semantic-flags-20260702-r1/stage_b_summary.json`,
  count `28000000002`, last BPC `0x15559475a8`, no trap, no panic, and no fail
  marker.
- `workloads/generated/specint-build-502-wrapv-20260702-r1/build_manifest.json`
  rebuilt 502 with default flags plus only `-fwrapv`. This single flag also
  suppressed the immediate internal error through the 240 second cap:
  `workloads/generated/specint-502-wrapv-20260702-r1/stage_b_summary.json`
  classified as `live-timeout`, count `32000000001`, last BPC `0x15556b207c`,
  no trap, no panic, and no fail marker.

Interpretation: `-fwrapv` is the narrowest tested build flag that changes the
default 502 failure class. This points at signed-overflow-sensitive behavior in
the Linx-built `cpugcc_r` binary or in Linx LLVM's lowering of code that relies
on wrapped signed arithmetic. It is still only a localization probe because the
row has not produced strict-hash-validated assembly output. After the probe,
502 was restored again to default flags; restore evidence is
`workloads/generated/specint-build-502-default-restore-after-wrapv-20260702-r1/build_manifest.json`.

`525.x264_r` note: this long train run used the pre-fail-fast generated 9p
command and therefore ran all four generated x264 train invocations after the
first timeout. The fast gate now auto-enables `--fail-9p-timeout` for generated
`*-large-9p` shards unless the caller explicitly overrides `--transports`, so
future all-train gates stop this shard on the first heartbeat-backed timeout.

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
- Classified SPEC benchmark stderr internal-error blocks as
  `spec-benchmark-internal-error`, including CR-normalized QEMU log marker
  blocks such as the current `502.gcc_r` train failure.
- Split large-payload SPEC rows in `run_specint_fast_gate.py`: by default the
  all-row suites keep `525.x264_r` but run it as `test-all-large-9p` /
  `train-all-large-9p`, while explicit `--transports` still forces a single
  transport for focused bisection.
- Added generated large-9p fail-fast policy so `525.x264_r` train/test shards
  do not spend a full gate running every generated row after the first 9p
  timeout.
- Added effective-argv evidence to SPEC init wrappers and per-run JSON:
  generated QEMU logs now emit `LINX_SPEC_ARGV_BEGIN/END` with indexed argv
  values, and each run records both `configured_argv` and `effective_argv`.
  This makes `LINX_SPEC_ARGV<n>_OVERRIDE` focused probes self-describing after
  the fact, including the `502.gcc_r` flag-override/debug lane.

## Profile observations

Profiles:

- `workloads/generated/specint-test-train-all-after-blockify-20260702-r2/profiles/qemu-train-active.sample.txt`
- `workloads/generated/specint-test-train-all-after-blockify-20260702-r2/profiles/qemu-train-520-active.sample.txt`
- `workloads/generated/specint-train-split-post-perlbench-20260702-r1/profiles/qemu-531-active.sample.txt`

Hot paths seen in both profiles:

- `helper_linx_template_step`
- `helper_linx_check_bstart_target`
- `probe_access_flags` and `mmu_lookup` under BSTART legality checks
- `linx_trace_wb` and `linx_call_trace_emit`, even in non-trace SPEC runs

The latest `531.deepsjeng_r` sample still shows the same throughput owners:
`helper_linx_template_step` around 313 samples, `probe_access_internal` around
291, `helper_linx_check_bstart_target` around 188, `mmu_lookup1` around 178,
`helper_linx_tile_set_attr` around 146, plus visible `linx_trace_wb`,
`helper_lookup_tb_ptr`, and `linx_call_trace_emit` frames. The next speed loop
should focus on reducing template-step and BSTART/probe/MMU helper cost before
raising SPEC train timeouts.

## Proposed next loops

1. QEMU speed: cache BSTART legality per TB or per guest code page and avoid repeated helper-side `probe_access_flags` for the same target. This is the hottest repeated path in both profiles.
2. QEMU speed: split `helper_linx_template_step` into fast paths for common non-template/non-trace execution and keep trace hooks fully disabled unless an explicit trace switch is set.
3. QEMU debug: add an exit counter summary with TB count, dynamic instruction count, BSTART checks, BSTART cache hits/misses, template helper calls, MMU probes, trace hook calls, heartbeat stall count, and last BPC.
4. SPEC gate: classify `live-timeout` as a performance failure distinct from correctness failures. Keep the correctness gate on hash-matching rows, and run timeout rows in a separate throughput budget.
5. `525.x264_r`: the fast gate now splits x264 to 9p by default. Treat both
   test and train focused 9p runs as `live-timeout` throughput rows; use
   initramfs only to reproduce the oversized-cpio panic.
6. `502.gcc_r`: treat train as a compiler/codegen bug first. The default
   binary exits with code 4 and reports a benchmark internal compiler error at
   `tree-into-ssa.c:942`. A conservative rebuild suppresses that internal error
   for at least 600 seconds but only reaches `live-timeout`; follow-up bisection
   narrowed the first suppressing flag to `-fwrapv`. The next loop is to isolate
   the signed-overflow-sensitive source object/function or Linx LLVM lowering
   feature that changes GCC tree-SSA behavior. This is not yet a correctness
   fix.
7. SIGKILL rows are now split by evidence. `541.leela_r` is real guest OOM at
   2 GiB, but at 4 GiB the old user trap was compiler-rt atomic recursion and
   is now fixed. The next `541` blocker is mallocng-specific so far: the fixed
   mallocng binary has hit both `get_meta` `assert(area->check == ctx.secret)`
   and `queue()` `assert(!m->next)`, while the oldmalloc relink stays live
   through 1200 seconds with no trap or OOM. Keep mallocng as the maintained
   default, but use `MALLOC_IMPL=oldmalloc` as a bisection lane before changing
   QEMU/compiler/libc for allocator metadata traps. Prior `520` did not
   reproduce SIGKILL and showed `oom_kill 0`; keep it in live-timeout/
   performance triage unless a fresh run proves otherwise. `523.xalancbmk_r` is
   unstable between user-trap and live-timeout; rerun with fault trace filters
   around the user BPC if the trap reproduces.
8. `500.perlbench_r` test run 2: investigate kernel Oops/SIGSEGV separately from train. The test row traps before hash verification; train hashes all match.
9. All other train failures in the current split run are heartbeat-backed
   live-timeouts, not deadlocks. Keep correctness work on the explicit
   internal-error/trap rows and run live-timeout rows through the QEMU
   throughput profile loop.

## Verification

- `PYTHONPATH=tools/spec2017 python3 -m unittest -q tools.spec2017.test_run_int_rate_qemu tools.spec2017.test_run_stage_qemu_matrix`
- `git diff --check -- tools/spec2017/run_int_rate_qemu.py tools/spec2017/test_run_int_rate_qemu.py`
- `python3 -m py_compile tools/spec2017/run_int_rate_qemu.py tools/spec2017/test_run_int_rate_qemu.py`
- `PYTHONPATH=tools/spec2017 python3 -m unittest tools.spec2017.test_run_int_rate_qemu`
- Focused current-code repro:
  `workloads/generated/specint-502-internal-error-class-20260702-r3/qemu_matrix_summary.json`
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
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 541.leela_r --memory-mb 4096 --stack-limit 2G --qemu-fault-trace-regs --qemu-fault-trace-addr 0 --qemu-fault-trace-pc-lo 0x1555615580 --qemu-fault-trace-pc-hi 0x15556155b0 --timeout 300` (expected red; mallocng trap did not reproduce, classified `live-timeout`)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 541.leela_r --memory-mb 4096 --stack-limit 2G --qemu-fault-trace-regs --qemu-fault-trace-addr 0 --timeout 900` (expected red; captured mallocng `queue()` assert at `0x1555616858`)
- `MALLOC_IMPL=oldmalloc MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh` (passed; allocator bisection sysroot)
- `bash tools/build_linx_llvm_cpp_runtimes.sh --profile spec --mode phase-b` (passed after oldmalloc sysroot refresh)
- `LINX_SPEC_LINK_MODE=default bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 541.leela_r --emit-manifest workloads/generated/specint-build-541-oldmalloc-20260702-r1/build_manifest.json` (passed; oldmalloc-linked `541`)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 541.leela_r --memory-mb 4096 --stack-limit 2G --timeout 420` against the oldmalloc-linked binary (expected red; `live-timeout`, no trap/panic/OOM)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 541.leela_r --memory-mb 4096 --stack-limit 2G --timeout 1200` against the oldmalloc-linked binary (expected red; `live-timeout`, count `133000000000`, no trap/panic/OOM)
- `skill-evolve: update linx-compiler (record compiler-rt/C11 atomic recursion triage and fallback verification)`
- `skill-evolve: update linx-lib (record oldmalloc bisection for mallocng metadata traps)`
- `python3 -m unittest tools.bringup.test_run_specint_fast_gate` (passed)
- `python3 -m py_compile tools/bringup/run_specint_fast_gate.py tools/bringup/test_run_specint_fast_gate.py` (passed)
- `python3 tools/bringup/run_specint_fast_gate.py --profile test-train --dry-run ...` (passed; generated `test-all-large-9p` and `train-all-large-9p` x264 shards)
- `python3 tools/spec2017/run_stage_qemu_matrix.py ... --bench 525.x264_r --input-set train --transports 9p --memory-mb 4096 --stack-limit 2G --timeout 480 --fail-9p-timeout` (expected red; `live-timeout`, no trap/panic/mount failure)
- `LINX_SPEC_ARGV2_OVERRIDE=10 python3 tools/spec2017/run_int_rate_qemu.py ... --bench 999.specrand_ir --input-set test --transport initramfs --run-index 1 --no-strict-hash` (passed; `workloads/generated/specint-argv-log-smoke-20260702-r1/stage_b_summary.json` records configured argv count `24239`, effective argv count `10`, and the QEMU log emits matching `LINX_SPEC_ARGV` lines)
- `python3 tools/spec2017/run_int_rate_qemu.py ... --bench 502.gcc_r --input-set train --transport initramfs --run-index 1` on the default binary (expected red; `workloads/generated/specint-502-current-argv-20260702-r1/stage_b_summary.json`, classified `spec-benchmark-internal-error` with argv evidence)
- `bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 502.gcc_r --optimize '-O0 -fno-vectorize -fno-slp-vectorize -fno-inline -fno-optimize-sibling-calls -fno-strict-aliasing -fwrapv -fno-jump-tables' --emit-manifest workloads/generated/specint-build-502-conservative-20260702-r1/build_manifest.json` (passed)
- `python3 tools/spec2017/run_int_rate_qemu.py ... --bench 502.gcc_r --input-set train --transport initramfs --run-index 1 --timeout 240` against the conservative binary (expected red; `live-timeout`, no internal error/trap/panic)
- `python3 tools/spec2017/run_int_rate_qemu.py ... --bench 502.gcc_r --input-set train --transport initramfs --run-index 1 --timeout 600` against the conservative binary (expected red; `live-timeout`, count `91000000002`, no internal error/trap/panic)
- `bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 502.gcc_r --optimize '-O0 -fno-vectorize -fno-slp-vectorize' --emit-manifest workloads/generated/specint-build-502-default-restore-20260702-r1/build_manifest.json` (passed; restored the default 502 binary after the conservative probe)
- `bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 502.gcc_r --optimize '-O0 -fno-vectorize -fno-slp-vectorize -fno-jump-tables' --emit-manifest workloads/generated/specint-build-502-no-jumptables-20260702-r1/build_manifest.json` (passed; focused probe still reproduced `tree-into-ssa.c:942`)
- `bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 502.gcc_r --optimize '-O0 -fno-vectorize -fno-slp-vectorize -fno-inline' --emit-manifest workloads/generated/specint-build-502-no-inline-20260702-r1/build_manifest.json` (passed; focused probe still reproduced `tree-into-ssa.c:942`)
- `bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 502.gcc_r --optimize '-O0 -fno-vectorize -fno-slp-vectorize -fno-optimize-sibling-calls -fno-strict-aliasing -fwrapv' --emit-manifest workloads/generated/specint-build-502-semantic-flags-20260702-r1/build_manifest.json` (passed; QEMU row became `live-timeout`)
- `bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 502.gcc_r --optimize '-O0 -fno-vectorize -fno-slp-vectorize -fwrapv' --emit-manifest workloads/generated/specint-build-502-wrapv-20260702-r1/build_manifest.json` (passed; `-fwrapv` alone made the row `live-timeout`, count `32000000001`)
- `bash tools/spec2017/build_int_rate_linx.sh --mode phase-b --force-static --bench 502.gcc_r --optimize '-O0 -fno-vectorize -fno-slp-vectorize' --emit-manifest workloads/generated/specint-build-502-default-restore-after-wrapv-20260702-r1/build_manifest.json` (passed; restored the default 502 binary after the flag bisection)
- `skill-evolve: update linx-superproject (record large SPEC payload transport split)`
