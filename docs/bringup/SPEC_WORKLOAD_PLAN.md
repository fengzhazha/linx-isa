# SPEC Workload Plan

This page is the canonical planning surface for SPEC CPU2017 on LinxISA.

Legacy script flags such as `--stage a`, `--stage b`, `phase-b`, and `phase-c`
remain implementation details of existing helpers. They are not the canonical
planning taxonomy anymore.

The canonical taxonomy is capability-based:

- **Control Path**: wrapper, QEMU path, artifact handoff, reproducible launch.
- **Userspace Entry**: trivial firmwareless Linux + initramfs userspace startup.
- **Fast Gate**: cheap SPECint `test`/`train` suites for QEMU/Linux regressions.
- **Bringup Subset**: first useful SPEC subset for runtime debugging.
- **Hosted Runtime**: shared musl / dynamic-loader path for hosted benches.
- **Subset Closure**: bringup subset passes qemu + specdiff on required transports.
- **Scale-Out**: promotion set closure and LinxCore xcheck.

## Policy Sets

- `spec_policy.bringup_subset`
  Current set: all supported Linx SPECint C/C++ rate rows on `train` input:
  `500.perlbench_r`, `502.gcc_r`, `505.mcf_r`, `520.omnetpp_r`,
  `523.xalancbmk_r`, `525.x264_r`, `531.deepsjeng_r`, `541.leela_r`,
  `557.xz_r`, and `999.specrand_ir`.
- `spec_policy.fast_gate`
  Current suites:
  - `test-smoke`: `999.specrand_ir` on `test`
  - `train-smoke`: `999.specrand_ir` on `train`
  - `train-all`: all supported Linx SPECint C/C++ rate rows on `train`
  - `test-cpu-stress`: `531.deepsjeng_r` on `test`, isolated in nightly
    because it can run for minutes before guest progress
  - `test-vm-stress`: `505.mcf_r` on `test`, isolated because it is the
    known large-allocation/MMU stressor
  - `train-cpu-stress`: `531.deepsjeng_r` on `train`, isolated in nightly
    because profiling showed it can run for minutes before guest progress
- `spec_policy.promotion_required`
  Current set: full required SPECint promotion set excluding policy exclusions
- `spec_policy.excluded_benchmarks`
  Current policy exclusion: `548.exchange2_r`

## Milestones

### SPEC-M01 Control Path Ready

Goal:
- The canonical Stage-A/bringup matrix command runs from the superproject with
  an explicit or inherited QEMU path and produces per-transport run staging.

Done means:
- `tools/spec2017/run_stage_qemu_matrix.py` forwards `QEMU=...` or `--qemu ...`
  plus per-run timeout, kernel append, and heartbeat controls to
  `run_int_rate_qemu.py`.
- Per-transport run directories are created under the chosen out dir.

Primary evidence:
- matrix summary JSON/MD
- transport logs

### SPEC-M01F Fast Test/Train Gate

Goal:
- A fast, repeatable SPECint gate runs `test` and `train` inputs before any
  refrate-scale or broad promotion work.

Done means:
- `tools/bringup/run_specint_fast_gate.py --profile pr` runs the fast suites
  through the active QEMU binary and emits `specint_fast_gate_summary.json`.
- The PR gate keeps `505.mcf_r` and `531.deepsjeng_r` out of the fast smoke
  path so cheap `test`/`train` regressions are visible first.
- The train profile supports `--suite train-all` so all ten supported SPECint
  rows can be run with bounded train input before promotion-scale runs.
- Nightly uses `--profile nightly` to add CPU stress, VM stress, and promotion
  breadth.

Primary evidence:
- `workloads/generated/specint-fast-gate/specint_fast_gate_summary.json`
- per-suite `qemu_matrix_summary.json`

### SPEC-M02 Firmwareless Linux Userspace Entry

Goal:
- A trivial static initramfs userspace payload starts visibly under the same
  firmwareless Linux/QEMU path that SPEC uses.

Done means:
- Static hello control lane emits guest-visible start/pass markers.
- Failure, if any, is no longer a zero-output timeout.

Primary evidence:
- corrected control-lane summary
- corrected `qemu_hello_static.log`

### SPEC-M03 Bringup Subset Output Generation

Goal:
- The benches in `spec_policy.bringup_subset` create their expected output
  files before specdiff runs.

Done means:
- `rand.24239.out`, `inp.out`, `mcf.out`, and `test.out` exist in the Linx run
  directories for the bringup subset.

Primary evidence:
- per-transport Stage-A summaries
- output files present in run dirs

### SPEC-M04 Hosted Runtime Restoration

Goal:
- The shared musl / dynamic-loader route is restored and reproducible.

Done means:
- `MODE=phase-c bash tools/spec2017/build_int_rate_linx.sh --build-runtimes`
  is green again.
- Dynamic hello or equivalent hosted control lane reaches guest-visible output.
- Shared-runtime SPEC benches no longer fail at setup because of missing
  `libc.so` / loader artifacts.

Primary evidence:
- `phase-c` build summary
- hosted control-lane summary

### SPEC-M05 Bringup Subset Closure

Goal:
- The bringup subset passes qemu + specdiff on required fast-gate transports.

Done means:
- `spec_policy.fast_gate` is green on the promoted initramfs transport.
- optional transport expansion can add `9p,initramfs` via the fast gate
  `--transports` override without redefining the baseline.
- aggregate fast-gate summary reports `ok=true`.

Primary evidence:
- fast-gate summary JSON/MD
- per-suite matrix summary JSON/MD
- per-transport summaries
- specdiff logs

### SPEC-M06 Promotion Set Closure And XCheck

Goal:
- The promotion set runs successfully on the runtime lane and is ready for
  LinxCore trace/xcheck expansion.

Done means:
- `spec_policy.promotion_required` is green on the promoted transport policy.
- phase-b static image prep is reproducible for the promotion set.
- LinxCore xcheck suite generation and report lane are green enough for
  promotion.

Primary evidence:
- promotion-set matrix summary
- phase-b image manifest
- xcheck suite/report artifacts

### SPEC-P01 Policy Exclusion

Goal:
- Keep `548.exchange2_r` explicitly excluded until the project deliberately
  expands scope to Fortran/runtime support.

Done means:
- exclusion remains documented in the manifest and checklists.
- promotion-set helpers do not silently reintroduce it.

## Current Live Interpretation

As of 2026-06-30:

- `SPEC-M01` is resolved.
- `SPEC-M01F` is the canonical fast gate shape for current QEMU/Linux SPECint
  work: run minimal `test-smoke` and `train-smoke` for cheap regression
  signal, then use `--profile train --suite train-all` for the all-ten train
  ledger before any refrate-scale or broad promotion run.
- `SPEC-M02` is resolved for the SPEC initramfs userspace path: the wrapper
  reaches SPEC startup and `999.specrand_ir` passes strict train hash on the
  active QEMU/kernel stack.
- `SPEC-M03` and `SPEC-M05` are active, not blocked by entry: current
  initramfs train-all evidence passes `999.specrand_ir`, reproduces a focused
  Linux VM/VMA correctness stop for `502.gcc_r`, reproduces the `525.x264_r`
  initramfs VFS-root panic, and classifies the remaining failed rows as
  heartbeat-backed live-slow rather than deadlock.
- `SPEC-M04` remains separately open for the shared-runtime path.
- `SPEC-M06` is not actionable until `SPEC-M05` train correctness and
  throughput lanes are green on the promoted static transport policy.
