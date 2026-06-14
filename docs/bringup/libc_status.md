# Linx libc Bring-up Status

Canonical libc sources:

- `lib/glibc`
- `lib/musl`

## Repositories and pins

- `lib/glibc` @ `69493c1b395a23546cab196947d6424003a9f5ed`
- `lib/musl` @ `5b90c23dde11df89f37cf004256dff738510b469`

## Current policy

- Bring-up deltas live in fork history (`LinxISA/glibc`, `LinxISA/musl`).
- This repository provides orchestration, runtime smoke, and status tracking.
- Release-strict gating uses canonical artifacts from `docs/bringup/gates/latest.json`.

## Current status (2026-06-14)

- glibc `G1a`: pass (`configure` + `csu/subdir_lib` + startup objects)
- glibc `G1b`: pass (`out/libc/glibc/logs/g1b-summary.txt`)
- glibc full-system runtime hello matrix: fail on the current tree
  (`avs/qemu/out/glibc-smoke/summary.json` reports
  `glibc_runtime_variant_failure`; the current wrapper/init path still exits
  without producing the expected `WRAP_INIT_START` / `GLIBC_HELLO_*` markers)
- musl `M1`: pass after syncing `arch/linx64` `float.h` to the compiler's
  64-bit `long double` ABI
- musl `M2`: pass in `phase-b`
- musl `M3`: blocked in `phase-b`
  (`out/libc/musl/logs/phase-b-summary.txt`,
  `out/libc/musl/logs/phase-b-m3-shared-notext-probe.log`)
- musl static Linux/QEMU smoke: fail on the current tree
  (`avs/qemu/out/musl-smoke/summary_static.json` reports
  `malloc_printf_static_runtime_timeout`; guest log shows
  `Kernel panic - not syncing: Attempted to kill init! exitcode=0x00000004`)
- musl shared Linux/QEMU smoke: unavailable while `M3` remains blocked
  (`avs/qemu/out/musl-smoke/summary_shared.json` reports missing shared runtime
  artifacts)

## Evidence pointers

- Canonical gate artifact: `docs/bringup/gates/latest.json`
- Rendered gate table: `docs/bringup/GATE_STATUS.md`
- glibc build logs: `out/libc/glibc/logs/summary.txt`, `out/libc/glibc/logs/g1b-summary.txt`
- musl build summary: `out/libc/musl/logs/phase-b-summary.txt`
- musl runtime logs: `avs/qemu/out/musl-smoke/summary.json`,
  `avs/qemu/out/musl-smoke/summary_static.json`,
  `avs/qemu/out/musl-smoke/qemu_malloc_printf_static.log`
- glibc runtime gate: `avs/qemu/run_glibc_smoke.py`,
  `avs/qemu/out/glibc-smoke/summary.json`

## Notes

- Release-strict sign-off does not allow blocked waivers for required libc gates.
- Runtime numeric/benchmark parity remains outside libc bring-up scope.
- `avs/qemu/run_glibc_smoke.py` is still the intended full in-tree glibc
  hello-matrix gate, but the current full-system lane is not green.
- The pinned `emulator/qemu` checkout currently exposes only
  `linx32-softmmu` and `linx64-softmmu`; `qemu-linx` linux-user flow is an
  optional external lane, not an in-tree validated artifact.
- The decisive loader-side change for the glibc runtime lane remains the Linx
  NOMMU-compatible contiguous-image PT_LOAD path in glibc, but the current
  PID1 wrapper / runtime visibility path still needs additional repair before
  the matrix can be called green again.
