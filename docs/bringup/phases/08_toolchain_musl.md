# Phase 8: Toolchain/musl Bring-up

Canonical source repository:

- `lib/musl` (`git@github.com:LinxISA/musl.git`)

## Objective

Bring up a reproducible Linx musl path for:

- `linx64-unknown-linux-musl` (`M1/M2/M3`)
- Linux initramfs runtime smoke with a real C program using `malloc/free/printf` (`R1/R2`)

## Entry points

- musl build entrypoint:
  - `lib/musl/tools/linx/build_linx64_musl.sh`
- runtime harness:
  - `avs/qemu/run_musl_smoke.py`
- runtime sample program:
  - `avs/qemu/tests/linux_musl_malloc_printf.c`

## Default artifact layout

- musl build/install/logs:
  - `out/libc/musl/build`
  - `out/libc/musl/install`
  - `out/libc/musl/logs`
- smoke outputs:
  - `avs/qemu/out/musl-smoke/initramfs.cpio`
  - `avs/qemu/out/musl-smoke/musl_smoke`
  - `avs/qemu/out/musl-smoke/qemu.log`
  - `avs/qemu/out/musl-smoke/summary.json`

## Modes

- `phase-b`:
  - strict mode (`LINX_MUSL_MODE=phase-b`)
  - no temporary excludes allowed
- `phase-a`:
  - optional compatibility mode for temporary exclusions via `LINX_MUSL_EXTRA_EXCLUDES`
  - records active excludes and crash signature in `out/libc/musl/logs/phase-a-exclusions.md`

## Commands

Build musl (`M1/M2/M3`):

```bash
cd lib/musl
MODE=phase-b ./tools/linx/build_linx64_musl.sh
```

Run end-to-end smoke (`R1/R2`):

```bash
cd .
python3 avs/qemu/run_musl_smoke.py --mode phase-b
```

## Current status (2026-06-14)

- `M1`: pass on the current toolchain after syncing `arch/linx64/bits/float.h`
  to the compiler's deliberate 64-bit `long double` ABI.
- `M2`: pass in `phase-b` (strict, no temporary excludes).
- `M3`: blocked in `phase-b`.
  Current blocker signatures from `out/libc/musl/logs/phase-b-summary.txt`:
  - `ld.lld: error: relocation R_LINX_PCREL_HI20 cannot be used against symbol '__stack_chk_guard'; recompile with -fPIC`
  - `ld.lld: error: relocation R_LINX_HL_PCR29_STORE cannot be used against symbol 'getdate_err'; recompile with -fPIC`
- `R1/R2`: not green on the current tree.
  - static runtime currently reaches `Kernel panic - not syncing: Attempted to kill init! exitcode=0x00000004`
    (`avs/qemu/out/musl-smoke/qemu_malloc_printf_static.log`)
  - shared runtime is unavailable until `M3` produces shared loader/libc
    artifacts
- Linux no-libc initramfs baselines (`smoke.py` / `full_boot.py`) still pass on
  the default QEMU system-mode path.

## Baseline repro pointers

- baseline freeze:
  - `out/libc/musl/logs/baseline.md`
- latest Linux userspace boot results:
  - `python3 ${LINUX_ROOT}/tools/linxisa/initramfs/smoke.py`
  - `python3 ${LINUX_ROOT}/tools/linxisa/initramfs/full_boot.py`

## Exit criteria

- `M1/M2` pass in strict mode (`phase-b`) with no temporary excludes.
- `M3` passes in `phase-b` (`out/libc/musl/logs/phase-b-summary.txt` shows `m3=pass`).
- runtime sentinels are observed under QEMU:
  - `MUSL_SMOKE_START`
  - `MUSL_SMOKE_PASS`
