# libc / Runtime Checklist

- [x] ID: LIBC-001 Build musl sysroots for required modes (phase-b and phase-c when requested).
  Command: `MODE=phase-b lib/musl/tools/linx/build_linx64_musl.sh`
  Done means: the required musl install tree exists under `out/libc/musl/install/<mode>` and the summary reports `M1/M2/M3` pass.
  Status: ✅ PASS (2026-06-28) - `MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh` completes with `m1=pass`, `m2=pass`, and `m3=pass` after the Linx `kstat` layout refresh and empty legacy archive install (`summary: out/libc/musl/logs/phase-b-summary.txt`).

- [x] ID: LIBC-005 Build glibc baseline G1a artifacts in the pinned workspace.
  Command: `bash lib/glibc/tools/linx/build_linx64_glibc.sh`
  Done means: the standard Linx glibc build path completes and produces the expected build tree under `out/libc/glibc/build`.
  Status: ✅ PASS (2026-03-08) - the pinned glibc baseline build completes successfully before G1b verification, with artifacts under `out/libc/glibc/build`.

- [x] ID: LIBC-002 Build glibc G1b shared libc gate artifacts.
  Command: `bash lib/glibc/tools/linx/build_linx64_glibc_g1b.sh`
  Done means: `out/libc/glibc/logs/g1b-summary.txt` reports pass or explicit waived block.
  Status: ✅ PASS (2026-03-08) - `g1b-summary.txt` reports `status: pass` and `classification: shared_libc_so_built`, with `out/libc/glibc/build/linkobj/libc.so` present.

- [ ] ID: LIBC-003 Pass musl runtime smoke for static and shared modes.
  Command: `python3 avs/qemu/run_musl_smoke.py --mode phase-b --link both`
  Done means: summary json for static/shared reports `ok=true`.
  Status: ❌ FAIL (2026-06-28 local) - `python3 avs/qemu/run_musl_smoke.py --mode phase-b --link both --sample all --qemu emulator/qemu/build-linx/qemu-system-linx64 --timeout 90` reports `runtime_mode_failure` (`avs/qemu/out/musl-smoke/summary.json`). Static runtime passes `malloc_printf`, `hello`, `callret`, fork/exec samples, `printf_string_arg`, `file_stdio`, and `cpp17_smoke`, then times out in `ebarg_timer` after `SEBARG_INIT_START`. Shared runtime passes `malloc_printf`, `hello`, `callret`, and `fork_wait`, then times out in `fork_wait_raw_exit` with a kernel Oops before init is killed. Proposed solution: isolate `ebarg_timer` first with timer/EBARG heartbeat tracing, and isolate shared `fork_wait_raw_exit` with syscall/fork breadcrumbs plus kernel symbolization of `tpc=0xffffffff80174a4c` before treating SPEC shared-runtime failures as benchmark-local.
  Focused pass: `python3 avs/qemu/run_musl_smoke.py --mode phase-b --link static --sample time_syscalls --qemu emulator/qemu/build-linx/qemu-system-linx64 --timeout 60 --out-dir avs/qemu/out/musl-time-syscalls-20260628` passes after the Linx `gettimeofday` copyout fix. This guards the legacy time syscall path that previously returned `-EFAULT` in `502.gcc_r`.

- [x] ID: LIBC-007 Keep early Linx oldmalloc growth valid before `__init_libc()`.
  Command: `MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh && python3 avs/qemu/run_musl_smoke.py --mode phase-b --link static --sample cpp17_smoke --sample malloc_printf --sample time_syscalls --qemu emulator/qemu/build-linx/qemu-system-linx64 --append norandmaps --timeout 180 --out-dir avs/qemu/out/musl-static-oldmalloc-page-20260628`
  Done means: oldmalloc can service C++ static-startup allocations before `libc.page_size` is populated, and the focused static smoke still passes.
  Status: ✅ PASS (2026-06-28 local) - `avs/qemu/out/musl-static-oldmalloc-page-20260628/summary.json` reports `ok=true`. Focused SPEC traces for `520.omnetpp_r` and `523.xalancbmk_r` now show first `brk` growth to the next page instead of the earlier no-op `brk(current)`.
  Follow-up: any phase-b musl sysroot rebuild invalidates the SPEC C++ runtime overlay. Run `./tools/build_linx_llvm_cpp_runtimes.sh --profile spec --mode phase-b` before rebuilding SPEC C++ workloads; `out/cpp-runtime/musl-cxx17-spec/summary_phase-b.json` is the current overlay evidence.

- [x] ID: LIBC-009 Use mallocng as the default Linx phase-b allocator.
  Command: `MODE=phase-b bash lib/musl/tools/linx/build_linx64_musl.sh`
  Done means: the default phase-b summary records `malloc_impl=mallocng`, focused static smoke still passes, and oldmalloc remains available with `MALLOC_IMPL=oldmalloc` for targeted allocator bisection.
  Status: PASS (2026-06-29 local) - `out/libc/musl/logs/phase-b-summary.txt` records `malloc_impl=mallocng`; `avs/qemu/out/musl-static-mallocng-default-20260629/summary.json` reports `ok=true` for static `malloc_printf`, `cpp17_smoke`, and `time_syscalls`; `out/cpp-runtime/musl-cxx17-spec/summary_phase-b.json` was rebuilt after the musl sysroot refresh; `workloads/generated/specint-train-all-20260629-mallocng-cxx-refresh-r1/train-all/initramfs/stage_b_summary.json` proves the allocator switch does not close SPEC `500`/`502` correctness yet, while `999.specrand_ir` still passes strict hash.
  Follow-up: do not treat allocator selection alone as SPEC closure. Keep `MALLOC_IMPL=oldmalloc` for reproducing older brk/mmap overlap evidence, but keep mallocng as the default maintained allocator baseline.

- [x] ID: LIBC-008 Preserve Linx TP across syscall, malloc, and locale paths.
  Command: `LINX_HEARTBEAT_INTERVAL=10000000 LINX_TP_TRACE=1 LINX_TP_TRACE_LIMIT=200 python3 avs/qemu/run_musl_smoke.py --mode phase-b --link static --sample tp_preserve --qemu emulator/qemu/build-linx/qemu-system-linx64 --append 'lpj=1000000 loglevel=8 console=ttyS0 kfence.sample_interval=0 norandmaps' --timeout 180 --out-dir avs/qemu/out/musl-tp-preserve-debug-r2-20260628`
  Done means: a static musl payload observes a nonzero TP and the same TP value across `gettimeofday`, repeated `malloc`/`free`, and locale access, while QEMU can log user-to-kernel TP handoffs.
  Status: ✅ PASS (2026-06-28 local) - `avs/qemu/out/musl-tp-preserve-20260628-r2/summary.json`, `avs/qemu/out/musl-tp-preserve-debug-r2-20260628/summary.json`, and `avs/qemu/out/musl-tp-preserve-final-20260628/summary.json` report `ok=true`; the debug qemu log includes `LINX_HEARTBEAT ... tp=...` and `LINX_TP_TRACE event=service_user_to_kernel`.

- [x] ID: LIBC-004 Keep runtime status evidence updated in bring-up gate artifacts.
  Done means: gate report rows include evidence links for musl/glibc runtime checks.
  Status: ✅ PASS (2026-03-15) - `docs/bringup/gates/latest.json` includes refreshed musl/glibc runtime evidence for the latest pin-lane run, including the regressed `Library::glibc runtime dynamic hello` row and its log path.

- [x] ID: LIBC-006 Close glibc dynamic runtime on Linux/QEMU with full hello matrix.
  Command: `python3 avs/qemu/run_glibc_smoke.py --qemu /tmp/linx-qemu-clean-build/qemu-system-linx64 --timeout 30`
  Done means: every tracked glibc runtime variant in the current hello matrix reaches `main` under the Linux/QEMU lane without wrapper-side entry bypasses and without loader fatal errors.
  Status: ✅ PASS (2026-04-18) - the wrapper no longer reopens `/dev/console`, emits markers over the virt UART, and the full `entry_main`/`shared`/`startup`/`startup_norpath` hello matrix now passes against the clean pinned QEMU artifact (`avs/qemu/out/glibc-smoke/summary.json`).
