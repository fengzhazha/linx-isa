# Phase 3: Emulator (QEMU) Bring-up

QEMU implementation source of truth is the submodule:

- `emulator/qemu/`

Linx patch lineage is maintained in the LinxISA QEMU fork history, then pinned here via submodule SHA.

## Basic flow

1. Build Linx test object/executable.
2. Run with `qemu-system-linx64 -machine virt -kernel <image>`.
   For the merged Linx64 recovery lane, direct kernel/rootfs runs are
   firmwareless by default and should include `-bios none` unless a specific
   firmware artifact is intentionally under test.
3. Validate output and exit status through AVS suites.

## Test entrypoints

```bash
# Default suites
./avs/qemu/run_tests.sh

# Full suites
./avs/qemu/run_tests.sh --all --timeout 20
```

## Conventions

- UART MMIO base: `0x10000000`
- Exit MMIO: `0x10000004`
- Exit value written at `0x10000004` is used as QEMU process exit code
