# LinxISA v0.57 Changelog

v0.57 is the current LinxISA profile for PTO tile/data block execution.

## Changed Delta From v0.56

- Defined the current Linx block descriptor contract with split tile source and
  destination descriptors: `B.ITP` for source TileReg pairs and `B.OTA` for
  destination TileReg allocation.
- Added `TZERO` as TileReg id `0x00`; it is source-only and is illegal as a
  destination.
- Moved destination allocation size into `B.OTA.CellCountM1` using 128-byte
  CELL units.
- Kept source TileReg size out of `B.ITP`; hardware reads source allocation
  metadata from TileReg state.
- Added `B.META` as the element-domain shape, valid-region, and mask metadata
  descriptor.
- Added the current PTO hardware encoding map:
  - TEPL: 92 rows, `0x00..0x5B`
  - FIXP: 8 rows, `0x00..0x07`
  - TMA: 5 rows, `0x00..0x04`
  - CUBE: 2 rows, `0x00..0x01`
- Covered 125 concrete PTO instruction forms in 107 encoding rows.
- Merged equivalent instruction forms under one encoding row when the hardware
  operation is selected by form bits, including `TSTORE/TSTORE_FP`,
  `TEXTRACT/TEXTRACT_FP`, `TINSERT/TINSERT_FP`, `TCONCAT/TCONCATIDX`,
  `TFILLPAD` variants, and matrix/TMA suffix families.
- Kept `TFILLPAD` and `TCONCAT` as hardware-visible instructions.
- Excluded sync, communication, pipe lifecycle, and PTO IR-only surfaces from
  hardware encoding.
- Omitted nonexistent or non-hardware helper forms from the PTO hardware map.

## Downstream Updates

- LLVM lowers and prints the v0.57 split descriptor model.
- QEMU decodes `B.ITP`, `B.OTA`, and the v0.57 TMA/CUBE/FIXP/TEPL opcode ids.
- GFSIM carries v0.57 descriptor state through decode, block issue, bridge, and
  execution paths.
- PTOAS rejects IR/view-only helper lowering where no v0.57 hardware
  instruction exists and preserves distinct `TCONCATIDX` emission.
- PTO-Kernel exposes v0.57 TileOP APIs and host semantics for the benchmark
  path.
- SuperNPUBench compiles both LinxISA and PTO ISA benchmark trees against the
  v0.57 API and descriptor syntax.
- linx-model generated tables use the v0.57 descriptor names.
- pyCircuit notes no longer list IR-only helpers as hardware instructions.

## Validation

- `python3 tools/isa/check_pto_v057_encoding.py --spec isa/v0.57/state/pto_encoding.json`
- `python3 tools/isa/check_pto_v057_downstream.py --strict`
- `bash tools/ci/check_repo_layout.sh`
- LLVM v0.57 FileCheck coverage for FIXP/TINSERT/TTRANS.
- QEMU v0.57 direct-boot finisher probe returned the expected `0x55` code.
- GFSIM v0.57 TINSERT, FIXP, and TLOAD/TSTORE probes reached `val=0x5555 pass`.
- SuperNPUBench full build returned `RC:0` with 49 LinxISA ELFs, 56 PTO ISA
  ELFs, and zero failure markers.
