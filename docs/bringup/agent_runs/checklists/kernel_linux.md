# Kernel / Linux Checklist

- [x] ID: LINUX-001 Boot initramfs smoke on Linx QEMU.
  Command: `python3 kernel/linux/tools/linxisa/initramfs/smoke.py`
  Done means: smoke boot reaches expected userspace marker without trap loop.
  Status: ✅ PASS (2026-04-18) - smoke gate remains green in run `2026-04-18-r9-pin-linuxlibc-refresh` (log: `docs/bringup/gates/logs/2026-04-18-r9-pin-linuxlibc-refresh/pin/kernel_smoke.log`).

- [x] ID: LINUX-002 Boot full initramfs scenario on Linx QEMU.
  Command: `python3 kernel/linux/tools/linxisa/initramfs/full_boot.py`
  Done means: full boot reaches expected completion marker.
  Status: ✅ PASS (2026-04-18) - full initramfs boot remains green in run `2026-04-18-r9-pin-linuxlibc-refresh` (log: `docs/bringup/gates/logs/2026-04-18-r9-pin-linuxlibc-refresh/pin/kernel_full_boot.log`).

- [x] ID: LINUX-003 Keep `linxisa_virt_defconfig` compatible with 9p/virtfs SPEC workflows.
  Command: `python3 tools/bringup/check_linx_virt_defconfig_spec.py --report-out docs/bringup/gates/linxisa_virt_defconfig_audit.json`
  Done means: kernel config includes required 9p + virtio-mmio options and still boots.
  Status: ✅ PASS (2026-03-08) - defconfig audit again reports `linxisa_virt_defconfig_spec_compatible` with zero missing/mismatched options (artifact: `docs/bringup/gates/linxisa_virt_defconfig_audit.json`).

- [ ] ID: LINUX-004 Boot BusyBox rootfs from virtio-blk and reach userspace `/sbin/init`.
  Command: `QEMU="$(bash tools/bringup/run_qemu_build_clean.sh --qemu-root $PWD/emulator/qemu --out-dir /tmp/linx-qemu-clean-build --target qemu-system-linx64)" QEMU_EXTRA_ARGS='-bios none' python3 kernel/linux/tools/linxisa/busybox_rootfs/boot.py`
  Done means: BusyBox rootfs boots from `/dev/vda`, shell commands run, and poweroff path works.
  Status: ❌ FAIL (2026-05-19 local) - the next operational mismatch is now explicit: the merged Linx64 QEMU recovery lane must boot firmwareless (`-bios none`) for direct kernel/rootfs runs. `boot.py` is aligned locally, the old `arch/linx/include/asm/bug.h` directive failure is fixed, and local rebuild follow-up also cleared the immediate SMP/VDSO source collisions, the first Linx MM/core API drifts, the earlier `fs/nfs` and `fs/lockd` SelectionDAG crashes, and the follow-on `lib/random32.o` crash, but there is still no new BusyBox rootfs verdict because the fresh clean-build path now stops later at `lib/hexdump.o` before `vmlinux` links.

- [ ] ID: LINUX-005 Build pinned `vmlinux` with the propagated LLVM/QEMU workspace state.
  Command: `bash tools/bringup/run_linux_vmlinux_build_clean.sh --linux-root $PWD/kernel/linux --out-dir $PWD/kernel/linux/build-linx-fixed --clang $PWD/compiler/llvm/build-linxisa-clang/bin/clang --gmake /opt/homebrew/bin/gmake --target vmlinux`
  Done means: the pinned kernel tree produces `kernel/linux/build-linx-fixed/vmlinux` without source or link failures.
  Status: ❌ FAIL (2026-05-19 local) - the last canonical proof is still the April 18 run, but current local revalidation has moved well beyond the old `bug.h` inline-asm failure, the first Linx vDSO clean-build failures, and the initial Linx MM/core API drift. The rebuilt kernel now gets through the refreshed VDSO path, the first page-table/uaccess/syscall compatibility fixes, the earlier `fs/nfs` and `fs/lockd` SelectionDAG crashes, and the follow-on `lib/random32.o` crash before stopping on the same backend crash family at `lib/hexdump.o` (`hex_to_bin`) under `-O2`.
