# SPECint / QEMU Checklist

## Live Blockers (2026-06-28)

- [x] ID: SPEC-M01F Train-all gate shape exists.
  Command: `SPECINT_TRAIN_ALL_TIMEOUT=900 python3 tools/bringup/run_specint_fast_gate.py --profile train --out-dir workloads/generated/specint-train-all-20260628-heartbeat --qemu emulator/qemu/build-linx/qemu-system-linx64 --append-extra norandmaps --guest-heartbeat-sec 0 --heartbeat-sec 30 --qemu-heartbeat-interval 1000000000 --no-progress-timeout 180 --continue-on-fail`
  Evidence: `workloads/generated/specint-train-all-20260628-heartbeat/specint_fast_gate_summary.json`, `workloads/generated/specint-train-all-20260628-heartbeat/train-all/qemu_matrix_summary.json`, and `workloads/generated/specint-train-all-20260628-heartbeat/train-all/initramfs/stage_b_summary.json`.
  Status: suite wiring is present and covers `500.perlbench_r`, `502.gcc_r`, `505.mcf_r`, `520.omnetpp_r`, `523.xalancbmk_r`, `525.x264_r`, `531.deepsjeng_r`, `541.leela_r`, `557.xz_r`, and `999.specrand_ir`.

- [x] ID: SPEC-QEMU-HB-001 BPC heartbeat switch exists.
  Switches: `LINX_HEARTBEAT_INTERVAL` or `LINX_QEMU_HEARTBEAT_INTERVAL`; fast-gate option `--qemu-heartbeat-interval`.
  Done means: qemu logs emit `LINX_HEARTBEAT` with count, delta, PC, BPC, TPC, branch state, selected argument registers, and `same_site`.
  Evidence: `workloads/generated/specint-heartbeat-smoke-20260628/test-smoke/initramfs/999_specrand_ir/run_001/qemu.log` and train-all per-benchmark `qemu.log` files.

- [x] ID: SPEC-M05-SMOKE `999.specrand_ir` train input passes under the all-train run.
  Evidence: `workloads/generated/specint-train-all-20260628-heartbeat/train-all/initramfs/999_specrand_ir/run_001/qemu.log` contains `LINX_SPEC_PASS 999.specrand_ir`.

- [ ] ID: SPEC-M05-EXECVE-500 `500.perlbench_r` must exec its static PIE image.
  Current blocker: `execve("./perlbench_r_base.mytest-m64")` returns `errno=2`.
  Evidence: `workloads/generated/specint-train-all-20260628-heartbeat/train-all/initramfs/500_perlbench_r/run_001/qemu.log`.
  Next probe: use the init-wrapper pre-exec `stat/open/read` diagnostics; if those succeed, instrument Linux `binfmt_elf` for no-interpreter `ET_DYN` and path lookup.

- [ ] ID: SPEC-M05-FD-502 `502.gcc_r` must read `200.c` correctly.
  Current blocker: `cpugcc_r_base.mytest-m64: fatal error: 200.c: Bad file number`.
  Evidence: `workloads/generated/specint-train-all-20260628-heartbeat/train-all/initramfs/502_gcc_r/run_001/qemu.log`.
  Next probe: trace `openat/read/lseek/fstat/close` for `200.c` and validate fd table plus musl errno mapping.

- [ ] ID: SPEC-M05-LIVE-SLOW The live slow train workloads need QEMU speedups or longer diagnostic budgets.
  Current blockers: `505.mcf_r`, `531.deepsjeng_r`, and `557.xz_r` timed out at 900s, but QEMU heartbeat counts and BPCs continued to advance.
  Evidence:
  - `505.mcf_r`: last heartbeat count `188000000001`, BPC `0x1555559c98`
  - `531.deepsjeng_r`: last heartbeat count `142000000000`, BPC `0x1555565200`
  - `557.xz_r`: last heartbeat count `154000000042`, BPC `0x1555576fac`
  Next probe: profile with heartbeat off or coarse; target page-local BSTART decode caching, TB chaining, and remaining helper-probe overhead.

- [ ] ID: SPEC-M05-CPP-TRAPS The C++ train workloads must stop trapping in userspace.
  Current blockers:
  - `520.omnetpp_r`: trap at `addr=0x27b010`, `a0=0x27b000`
  - `523.xalancbmk_r`: trap at `addr=0x4f5010`, `a0=0x4f5000`
  - `541.leela_r`: trap at `addr=0xffffffffffffffe8`
  Evidence: train-all per-benchmark `qemu.log` files under `workloads/generated/specint-train-all-20260628-heartbeat/train-all/initramfs/`.
  Next probe: symbolize against the benchmark ELFs and inspect static C++ runtime relocations, constructors, TLS, exception/unwind setup, and call/return ABI state.

- [ ] ID: SPEC-M05-PANIC-525 `525.x264_r` must boot far enough to execute userspace.
  Current blocker: early `LINX_PANIC caller=0xffffffff80001648`.
  Evidence: `workloads/generated/specint-train-all-20260628-heartbeat/train-all/initramfs/525_x264_r/run_001/qemu.log`.
  Next probe: reproduce with the same initramfs footprint and a tiny payload, then symbolize the panic caller and inspect early unpack/page-allocation paths.

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
