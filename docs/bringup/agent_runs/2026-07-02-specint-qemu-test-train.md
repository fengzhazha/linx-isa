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

## Tool fixes in this loop

- Fixed the GCC test input verifier to compare the generated `.s` output instead of a nonexistent `.out`.
- Added an opt-in printf self-test to the SPEC init wrapper for ABI debug.
- Fixed a false-red path where exact strict host hashes were overwritten by host `specdiff` rc=2. The train `500.perlbench_r` run artifact predates this fix, so its JSON still shows `specdiff-mismatch` even though every output hash matches.

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
7. SIGKILL rows (`520`, `523`, `541`): rerun with guest heartbeat enabled and `/proc/$pid/status` sampling to distinguish guest OOM, resource limit, or kernel kill path. No OOM line was visible in the current QEMU logs.
8. `500.perlbench_r` test run 2: investigate kernel Oops/SIGSEGV separately from train. The test row traps before hash verification; train hashes all match.

## Verification

- `PYTHONPATH=tools/spec2017 python3 -m unittest -q tools.spec2017.test_run_int_rate_qemu tools.spec2017.test_run_stage_qemu_matrix`
- `git diff --check -- tools/spec2017/run_int_rate_qemu.py tools/spec2017/test_run_int_rate_qemu.py`
