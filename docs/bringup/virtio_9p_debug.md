# virtio-9p bring-up status (Linx virt)

## Summary

We are bringing up host→guest file sharing for the Linx Linux bring-up using **virtio-9p over virtio-mmio**.

Current status:

- virtio-mmio transport(s): **working** (guest enumerates virtio devices)
- virtio-blk on virtio-mmio: **working** (guest sees `vda`)
- virtio-9p mount: **failing** with `EPROTO (-71)` when running `mount -t 9p render-share /opt/share ...`
- SPEC init 9p mount: **failing earlier** with raw syscall return `-EFAULT (-14)`
  for `mount("spec2017", "/spec", "9p", 0,
  "trans=virtio,version=9p2000.L")`

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

- expected today: `9p_mount=ffffffffffffffb9`  (== -71, EPROTO)

## Known pitfalls / notes

- If you pass `virtio_mmio.device=0x200@0x30001000:1` while the DT already contains virtio-mmio nodes, Linux may attempt to register a *second* virtio-mmio transport and hit probe conflicts (e.g. `-16`).
- Endianness assumption: **little-endian** for virtio and 9p protocol fields.
- 2026-06-30 SPEC evidence:
  `workloads/generated/specint-525-9p-rawmount-argdump-20260630-r1/525_x264_r/run_001/qemu.log`
  shows QEMU can read the SPEC 9p options string from the guest pointer while
  Linux returns `-EFAULT`. This points at the Linx Linux mount/user-copy path
  before the older virtio-9p `EPROTO` protocol lane.

## Related PRs

- QEMU: multi, modern virtio-mmio transports for linx virt (infrastructure for virtio bring-up)
  - https://github.com/LinxISA/qemu/pull/19
- Linux: initramfs `m9p` applet and `/opt/share` dirs for in-guest reproduction
  - https://github.com/LinxISA/linux/pull/15

## Next debug steps

- Add minimal QEMU-side logging for the first 9p exchange (Tversion/Rversion) to determine if the failure is:
  - feature negotiation mismatch
  - virtqueue descriptor parsing issue
  - payload endian/length decoding issue
