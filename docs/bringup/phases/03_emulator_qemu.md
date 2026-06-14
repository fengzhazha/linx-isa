# Phase 3: Emulator (QEMU) Bring-up

QEMU implementation source of truth is the submodule:

- `emulator/qemu/`

Linx patch lineage is maintained in the LinxISA QEMU fork history, then pinned here via submodule SHA.

## Basic flow

1. Build the Linx freestanding suite into an aggregate `ET_REL` object, then
   link the firmwareless direct-boot `ET_EXEC` image used by the current
   recovery lane.
2. Run with `qemu-system-linx64 -machine virt -kernel <image>`.
   For the merged Linx64 recovery lane, direct kernel/rootfs runs are
   firmwareless by default and should include `-bios none` unless a specific
   firmware artifact is intentionally under test.
3. Validate output and exit status through AVS suites.

Current local bring-up helper for the live dirty-source QEMU line:

```bash
bash tools/bringup/run_qemu_build_local.sh
```

That helper configures/rebuilds `/private/tmp/linx-qemu-local-build` and
prints the resulting `qemu-system-linx64` path.

## Linux-user process flow

Use QEMU linux-user mode as a fast process ABI smoke only when an external or
recovered `qemu-linx` build exists. This runner launches a Linx Linux userspace
ELF directly through host QEMU instead of booting `vmlinux`, so it sits before
the kernel/rootfs gate in the debug order.

```bash
python3 avs/qemu/run_musl_smoke.py \
  --mode phase-b \
  --link static \
  --runner user \
  --qemu-user emulator/qemu/build-user/qemu-linx
```

The command compiles and links the normal musl smoke binary, then runs:

```bash
qemu-linx -L out/libc/musl/install/phase-b avs/qemu/out/musl-smoke/<sample>_static
```

Treat a user-mode pass as evidence for ELF startup, syscall dispatch, and libc
process behavior. Still run the default system-mode smoke before closing a
kernel/rootfs or full-OS runtime change.

The pinned `emulator/qemu` submodule in this checkout currently exposes only
`linx32-softmmu` and `linx64-softmmu`. Until a Linx linux-user target is
reintroduced in the fork, the commands above document an optional external lane
rather than an in-tree build artifact.

The matching glibc static process smoke is:

```bash
python3 avs/qemu/run_glibc_smoke.py \
  --runner user \
  --qemu-user emulator/qemu/build-user/qemu-linx
```

This builds `hello_glibc_static` and runs it directly through linux-user QEMU.

## Test entrypoints

```bash
# Default suites
./avs/qemu/run_tests.sh

# Full suites
./avs/qemu/run_tests.sh --all --timeout 20
```

For the current full-system Linux bring-up proof on the Linx `virt` machine:

```bash
QEMU="$(bash tools/bringup/run_qemu_build_local.sh)" \
python3 avs/qemu/run_linux_boot_proofs.py
```

That wrapper runs two sequential proofs against the current rebuilt kernel and
initramfs flow:

- userspace-entry proof: `tinytrap` initramfs, proves the guest executes first
  userspace instructions
- native shutdown proof: `tiny` PID1, proves Linux can power off QEMU without
  semihost-only exit

## Conventions

- Firmwareless direct boot expects the freestanding QEMU suite image to carry
  a concrete entry point and an exported `__end_init_stack` symbol so the Linx
  `virt` machine can seed `sp` before `_start`.
- UART MMIO base: `0x10000000`
- Test finisher MMIO: `0x10009000`
- Finisher low 16 bits select pass/fail/reset (`0x5555` / `0x3333` / `0x7777`);
  the upper 16 bits carry an optional failure code
