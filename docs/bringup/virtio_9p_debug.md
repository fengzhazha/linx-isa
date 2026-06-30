# virtio-9p bring-up status (Linx virt)

## Summary

We are bringing up host→guest file sharing for the Linx Linux bring-up using **virtio-9p over virtio-mmio**.

Current status:

- virtio-mmio transport(s): **working** (guest enumerates virtio devices)
- virtio-blk on virtio-mmio: **working** (guest sees `vda`)
- virtio-9p SPEC mount: **working** for the SPEC init wrapper path
- generic initramfs `m9p` applet: **needs retest** against the same kernel/QEMU
  fixes before the older `EPROTO (-71)` render-share status is treated as
  current

## Minimal reproduction

### QEMU

Use Linx virt DT-provided transports (do **not** add `virtio_mmio.device=...` when DT already declares virtio-mmio nodes).

Example:

```bash
QEMU=~/linx-isa/emulator/qemu/build/qemu-system-linx64
KERNEL=~/linx-isa/kernel/linux/build-linx-render/vmlinux
INITRD=~/linx-isa/kernel/linux/build-linx-fixed/linx-initramfs/initramfs.cpio
SHARE=~/linx-isa/out/render-share

$QEMU \
  -machine virt -m 1024M -smp 1 \
  -kernel "$KERNEL" -initrd "$INITRD" \
  -append "console=ttyS0 lpj=1000000 loglevel=7" \
  -nographic -monitor none \
  -fsdev local,id=fsdev0,path="$SHARE",security_model=none,multidevs=remap \
  -device virtio-9p-device,fsdev=fsdev0,mount_tag=render-share
```

### Guest

In initramfs, run `m9p` (debug applet) to attempt the mount and print the raw return code:

- historical result before the latest SPEC 9p fixes:
  `9p_mount=ffffffffffffffb9`  (== -71, EPROTO)
- current action: rerun this applet with the kernel that includes the Linx
  bytewise usercopy path, explicit 9p init wrappers, and the virtio-mmio feature
  word fix.

## Known pitfalls / notes

- If you pass `virtio_mmio.device=0x200@0x30001000:1` while the DT already contains virtio-mmio nodes, Linux may attempt to register a *second* virtio-mmio transport and hit probe conflicts (e.g. `-16`).
- Endianness assumption: **little-endian** for virtio and 9p protocol fields.
- Historical 2026-06-30 SPEC evidence:
  `workloads/generated/specint-525-9p-rawmount-argdump-20260630-r1/525_x264_r/run_001/qemu.log`
  shows QEMU can read the SPEC 9p options string from the guest pointer while
  Linux returns `-EFAULT`. This points at the Linx Linux mount/user-copy path
  before the older virtio-9p `EPROTO` protocol lane.
- Fixed 2026-06-30 SPEC evidence:
  `workloads/generated/specint-525-9p-vmgetfeatures-wordfix-20260630-r1/525_x264_r/run_001/qemu.log`
  shows `LINX_VIRTIO_MMIO_FEATURES ... device=0x30000001`, the
  `9pnet_virtio` driver selecting the mount-tag feature, and both SPEC 9p
  mounts returning zero. The all-row 9p train fast gate under
  `workloads/generated/specint-train-all-9p-failtimeout-20260630-r1/`
  reaches `LINX_SPEC_START` for every supported SPECint train benchmark.
- Debug switches:
  - guest: add `linx_virtio_debug=1` and `linx_mount_debug=1` on the kernel
    command line.
  - QEMU: set `LINX_VIRTIO_MMIO_DEBUG=1` to trace virtio-mmio feature/status
    registers and `LINX_SYSCALL_TRACE_DUMP_ARGS=0,1,2,4` to dump mount syscall
    pointers/strings.
  - QEMU throughput: set `LINX_TLB_TRACE=1` with
    `LINX_TLB_TRACE_COUNT_LO=<post-start-count>` only when a host sample points
    at `helper_linx_tlb_iall`. The 2026-06-30 `999.specrand_ir` 9p trace showed
    early fixmap invalidations before `LINX_SPEC_START`, and the post-boot
    filtered run emitted no TLB trace records while heartbeat kept advancing.
  - Suite runs should leave these noisy switches off and rely on
    `LINX_HEARTBEAT_INTERVAL` / `LINX_QEMU_HEARTBEAT_INTERVAL` for BPC liveness.

## Related PRs

- QEMU: multi, modern virtio-mmio transports for linx virt (infrastructure for virtio bring-up)
  - https://github.com/LinxISA/qemu/pull/19
- Linux: initramfs `m9p` applet and `/opt/share` dirs for in-guest reproduction
  - https://github.com/LinxISA/linux/pull/15

## Next debug steps

- Retest the generic render-share `m9p` applet with the fixed kernel/QEMU and
  compare it with the SPEC `spec2017` tag.
- Profile 9p runtime overhead separately from QEMU core throughput. Even
  `999.specrand_ir` reaches a 180s `live-timeout` under the 9p fast gate while
  the initramfs strict-hash sentinel passes, so 9p is currently a transport
  bring-up path rather than the cheap correctness sentinel.
- If a 9p protocol failure reappears, use the new MMIO/syscall debug switches
  first; then add first-exchange Tversion/Rversion logging only if feature
  negotiation and mount syscall arguments are already known good.
