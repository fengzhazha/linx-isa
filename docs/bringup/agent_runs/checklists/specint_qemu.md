# SPECint / QEMU Checklist

## Live Blockers (2026-06-28)

- [x] ID: SPEC-M01F Train-all gate shape exists and covers every current Linx SPECint rate benchmark.
  Static build command: `MODE=phase-b bash tools/spec2017/build_int_rate_linx.sh --force-static --jobs 10 --emit-manifest workloads/generated/specint-train-all-20260628-static/build-manifest-v2.json`
  Static run command: `SPECINT_TRAIN_ALL_TIMEOUT=600 LINX_SPEC_HEARTBEAT_SEC=30 LINX_SPEC_QEMU_HEARTBEAT_INTERVAL=1000000000 LINX_SPEC_NO_PROGRESS_TIMEOUT=180 python3 tools/bringup/run_specint_fast_gate.py --profile train --out-dir workloads/generated/specint-train-all-20260628-static --qemu emulator/qemu/build-linx/qemu-system-linx64 --append-extra norandmaps --guest-heartbeat-sec 0 --heartbeat-sec 30 --qemu-heartbeat-interval 1000000000 --no-progress-timeout 180 --continue-on-fail`
  Latest static run after the Linux time-syscall fix: `SPECINT_TRAIN_ALL_TIMEOUT=600 LINX_SPEC_HEARTBEAT_SEC=30 LINX_SPEC_QEMU_HEARTBEAT_INTERVAL=1000000000 LINX_SPEC_NO_PROGRESS_TIMEOUT=180 python3 tools/bringup/run_specint_fast_gate.py --profile train --out-dir workloads/generated/specint-train-all-20260628-after-gtod --qemu emulator/qemu/build-linx/qemu-system-linx64 --append-extra norandmaps --guest-heartbeat-sec 0 --heartbeat-sec 30 --qemu-heartbeat-interval 1000000000 --no-progress-timeout 180 --continue-on-fail`
  Evidence: `workloads/generated/specint-train-all-20260628-static/build-manifest-v2.json`, `workloads/generated/specint-train-all-20260628-static/specint_fast_gate_summary.json`, `workloads/generated/specint-train-all-20260628-static/train-all/qemu_matrix_summary.json`, and `workloads/generated/specint-train-all-20260628-static/train-all/initramfs/stage_b_summary.json`.
  Latest evidence: `workloads/generated/specint-train-all-20260628-after-gtod/specint_fast_gate_summary.json`, `workloads/generated/specint-train-all-20260628-after-gtod/train-all/qemu_matrix_summary.json`, and `workloads/generated/specint-train-all-20260628-after-gtod/train-all/initramfs/stage_b_summary.json`.
  Status: suite wiring covers `500.perlbench_r`, `502.gcc_r`, `505.mcf_r`, `520.omnetpp_r`, `523.xalancbmk_r`, `525.x264_r`, `531.deepsjeng_r`, `541.leela_r`, `557.xz_r`, and `999.specrand_ir`.
  Static build result: all ten selected C/C++ benchmarks built as Linx executables; source immutability check passed.

- [x] ID: SPEC-QEMU-HB-001 BPC heartbeat switch exists.
  Switches: `LINX_HEARTBEAT_INTERVAL` or `LINX_QEMU_HEARTBEAT_INTERVAL`; fast-gate option `--qemu-heartbeat-interval`.
  Done means: qemu logs emit `LINX_HEARTBEAT` with count, delta, PC, BPC, TPC, branch state, selected argument registers, and `same_site`.
  Evidence: `workloads/generated/specint-heartbeat-smoke-20260628/test-smoke/initramfs/999_specrand_ir/run_001/qemu.log` and train-all per-benchmark `qemu.log` files under `workloads/generated/specint-train-all-20260628-static/train-all/initramfs/` and `workloads/generated/specint-train-all-20260628-after-gtod/train-all/initramfs/`.
  Result: `505.mcf_r`, `531.deepsjeng_r`, and `557.xz_r` timed out with changing user-space BPCs, so they are live-slow/performance cases, not deadlocks.

- [x] ID: SPEC-QEMU-SYSCALL-DBG-001 Syscall trace can identify path/fd failures without full traces.
  Switches: `LINX_SYSCALL_TRACE=1`, optional `LINX_SYSCALL_TRACE_NR`, `LINX_SYSCALL_TRACE_PC_LO/HI`, `LINX_SYSCALL_TRACE_LIMIT`, `LINX_SYSCALL_TRACE_STRINGS=1`, and `LINX_SYSCALL_TRACE_STRING_MAX`.
  Done means: qemu logs emit syscall entry/return pairs, entry arguments on returns, unpaired syscall markers, and separate `LINX_SYSCALL_ARGSTR` records for pathname arguments.
  Evidence: `workloads/generated/specint-502-syscall-argstr-smoke-20260628/run/initramfs/502_gcc_r/run_001/qemu.log` contains `LINX_SYSCALL_ARGSTR` records for `/dev/console`, `/spec-run`, SPEC output/input paths, and `.linx_empty_stdin`.

- [x] ID: SPEC-M05-SMOKE `999.specrand_ir` train input passes under the all-train run.
  Evidence: `workloads/generated/specint-train-all-20260628-after-gtod/train-all/initramfs/999_specrand_ir/run_001/qemu.log` contains `LINX_SPEC_PASS 999.specrand_ir`; `stage_b_summary.json` records `ok=true` for this benchmark.
  Note: a shared-runtime rebuild made `999.specrand_ir` a 15 KiB dynamic executable and it trapped in shared startup; the static phase-b executable is the current correctness gate until shared SPEC runtime is green.

- [x] ID: SPEC-M05-GTOD-502 Legacy `gettimeofday` no longer poisons 502 diagnostics.
  Resolution: Linx VDSO syscall fallbacks now load the syscall number in `a7`, and `sys_gettimeofday()` uses a Linx-local `copy_to_user()` copyout instead of the current faulting 64-bit `put_user()` path.
  Evidence: `workloads/generated/specint-502-static-gettimeofday-copyout-20260628/run/initramfs/502_gcc_r/run_001/qemu.log` shows syscall `169` returning `0` after the focused fix, and `avs/qemu/out/musl-time-syscalls-20260628/summary.json` passes the focused musl `time_syscalls` sample.
  Follow-up: the remaining `502.gcc_r` EBADF diagnostic is no longer explained by syscall `169`; the full post-fix trace contains no `-EBADF` syscall returns.

- [x] ID: SPEC-M05-EXECVE-500 `500.perlbench_r` static PIE is present and readable before `execve`.
  Resolution: the original `errno=2` classification was narrowed by the init-wrapper pre-exec probe; the benchmark path is valid in the initramfs.
  Evidence: `workloads/generated/specint-500-preexec-20260628/initramfs/500_perlbench_r/run_001/qemu.log` shows `stat=0`, `open=6`, `read4=4`, and ELF magic `0x7f454c46`.
  Follow-up: `500.perlbench_r` now reaches Perl user code and fails in `Math::BigInt` range handling.

- [x] ID: SPEC-M05-FIXUP-500 Linx Linux recognizes v0.56 faultable usercopy fixup blocks.
  Resolution: `arch/linx/mm/extable.c` now accepts nonzero-offset 32-bit and 48-bit `BSTART.{STD,SYS,FP} FALL<, fixup_label>` fixup encodings before the legacy 128-bit block-header fallback.
  Evidence: `workloads/generated/specint-500-fixup-20260628/initramfs/500_perlbench_r/run_001/qemu.log` no longer stops at the earlier `sys_fcntl` usercopy `HL.BSTART.STD FALL` Oops.
  Verification: `run_linux_vmlinux_build_clean.sh --target vmlinux` rebuilt `kernel/linux/build-linx-fixed/vmlinux`; focused 500 rerun advanced to a different Oops.

- [x] ID: SPEC-M05-KMALLOC-500 `500.perlbench_r` completes the earlier `filelock_cache` slab-cache path.
  Resolution: the Linx curated init path now initializes the file-lock slab cache, moving past the prior `kmem_cache_alloc_noprof` null-cache fault.
  Evidence: `workloads/generated/specint-500-after-filelock-20260628/`, `workloads/generated/specint-500-syscall-openat-ret-20260628/`, and `workloads/generated/specint-500-stdin-empty-20260628/`.

- [ ] ID: SPEC-M05-BIGINT-500 `500.perlbench_r` must complete Perl BigInt train input.
  Current blocker: `Range iterator outside integer range at lib/Math/BigInt.pm line 2675`.
  Evidence: `workloads/generated/specint-train-all-20260628-after-gtod/train-all/initramfs/stage_b_summary.json` classifies `500.perlbench_r` as `user-arithmetic-range`.
  Proposed solution: reduce to a Perl snippet with syscall tracing disabled; compare integer conversion/range behavior against host SPEC; then inspect compiler integer lowering, libc conversion state, and call/return ABI before changing benchmark sources.

- [ ] ID: SPEC-M05-FD-502 `502.gcc_r` must read `200.c` correctly.
  Current blocker: `cpugcc_r_base.mytest-m64: fatal error: 200.c: Bad file number`.
  Evidence: `workloads/generated/specint-502-static-fulltrace-post-gtod-20260628/run/initramfs/502_gcc_r/run_001/qemu.log` shows `openat("200.c") -> 3`, `fstat(3) -> 0`, `fcntl(3, F_GETFD) -> 0`, `newfstatat(3, "", ..., AT_EMPTY_PATH) -> 0`, `/proc/self/fd/3 -> 0`, and `close(3) -> 0`; the same trace has no syscall return of `-EBADF`.
  Proposed solution: stop treating this as a kernel fd-table failure. Instrument or symbolize `502.gcc_r` around `cpp_files.c:open_file/open_file_failed`, validate the compiled `errno`/`file->err_no` store path, and compare static musl errno/TLS plus compiler codegen before changing QEMU or SPEC packaging.

- [ ] ID: SPEC-M05-LIVE-SLOW The live slow train workloads need QEMU speedups or longer diagnostic budgets.
  Current blockers: `505.mcf_r`, `531.deepsjeng_r`, and `557.xz_r` timed out at 600s, but QEMU heartbeat counts and BPCs continued to advance.
  Evidence:
  - `505.mcf_r`: last heartbeat count `111000000000`, BPC `0x155555c8dc`
  - `531.deepsjeng_r`: last heartbeat count `80000000029`, BPC `0x155555b576`
  - `557.xz_r`: last heartbeat count `106000000002`, BPC `0x15555710f0`
  Proposed solution: profile with heartbeat off or very coarse; target page-local BSTART decode caching, TB chaining, template/queue fast helpers, and removal of disabled trace/env checks from hot helpers.

- [ ] ID: SPEC-M05-CPP-TRAPS The C++ train workloads must stop trapping in userspace.
  Current blockers:
  - `520.omnetpp_r`: trap at `addr=0x27b010`, `a0=0x27b000`
  - `523.xalancbmk_r`: trap at `addr=0x4f5010`, `a0=0x4f5000`
  - `541.leela_r`: trap at `addr=0xffffffffffffffe8`
  Evidence: train-all per-benchmark `qemu.log` files under `workloads/generated/specint-train-all-20260628-after-gtod/train-all/initramfs/`.
  Proposed solution: symbolize against the static benchmark ELFs and inspect C++ runtime constructors, static object relocation, TLS, exception/unwind setup, and call/return ABI state. Keep the C++ runtime overlay build (`tools/build_linx_llvm_cpp_runtimes.sh --profile spec --mode phase-b`) as a prerequisite for shared diagnostics.

- [ ] ID: SPEC-M05-PANIC-525 `525.x264_r` must boot far enough to execute userspace.
  Current blocker: early `LINX_PANIC caller=0xffffffff80001648`.
  Evidence: `workloads/generated/specint-train-all-20260628-after-gtod/train-all/initramfs/525_x264_r/run_001/qemu.log`.
  Proposed solution: reproduce with the same large initramfs footprint and a tiny payload, then symbolize the panic caller and inspect early initramfs unpack/page-allocation paths before treating this as an x264 userspace failure.

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
