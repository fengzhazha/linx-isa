# Version 0.56 CAS and DMA Instructions Update

Update date: July 15, 2026

## Update Summary

This update adds 32-bit atomic Compare-And-Swap (CAS) instructions and DMA operation to LinxISA v0.56, complementing the existing 48-bit HL.CAS* instruction family.

## New Instructions

### 32-bit Atomic Compare-And-Swap Instructions

Four new 32-bit CAS instructions have been added to the atomic operation group:

| Instruction | Opcode Encoding | Description |
|-------------|-----------------|-------------|
| **CASB** | `SrcD[4:0] aq rl SrcR[4:0] SrcL[4:0] 000 RegDst[4:0] 001 101 1` | Compare-and-swap byte (8-bit) |
| **CASH** | `SrcD[4:0] aq rl SrcR[4:0] SrcL[4:0] 001 RegDst[4:0] 001 101 1` | Compare-and-swap halfword (16-bit) |
| **CASW** | `SrcD[4:0] aq rl SrcR[4:0] SrcL[4:0] 010 RegDst[4:0] 001 101 1` | Compare-and-swap word (32-bit) |
| **CASD** | `SrcD[4:0] aq rl SrcR[4:0] SrcL[4:0] 011 RegDst[4:0] 001 101 1` | Compare-and-swap doubleword (64-bit) |

**Assembly Format:**
```assembly
casb<.{aq, rl, aqrl}> [SrcL], SrcR, SrcD, ->{t, u, Rd}
cash<.{aq, rl, aqrl}> [SrcL], SrcR, SrcD, ->{t, u, Rd}
casw<.{aq, rl, aqrl}> [SrcL], SrcR, SrcD, ->{t, u, Rd}
casd<.{aq, rl, aqrl}> [SrcL], SrcR, SrcD, ->{t, u, Rd}
```

**Operands:**
- `[SrcL]`: Memory address (base register)
- `SrcR`: Expected value for comparison
- `SrcD`: New value to swap in if comparison succeeds
- `RegDst`: Destination register receiving the original memory value

**Encoding Details:**
- **Major opcode**: `6..4=3'b001, 3..1=3'b101` (separate from DMA)
- **Width encoding**: `14..12` distinguishes byte/halfword/word/doubleword
  - `000` = CASB (byte)
  - `001` = CASH (halfword)
  - `010` = CASW (word)
  - `011` = CASD (doubleword)
- **Register fields**: Four independent 5-bit register operands
  - `31..27`: SrcD (swap value input)
  - `26`: aq (acquire flag)
  - `25`: rl (release flag)
  - `24..20`: SrcR (compare value)
  - `19..15`: SrcL (address)
  - `11..7`: RegDst (old value output)

**Memory Ordering:**
- Supports `.aq` (acquire), `.rl` (release), and `.aqrl` (acquire-release) suffixes
- Does **not** support `.f` (far) flag — use 48-bit `HL.CAS*` for remote cache operations

### DMA Operation

| Instruction | Opcode Encoding | Description |
|-------------|-----------------|-------------|
| **DMA** | `0000000 SrcR[4:0] SrcL[4:0] 111 00000 000 101 1` | DMA transfer operation |

**Assembly Format:**
```assembly
dma [SrcL], SrcR
```

**Operands:**
- `[SrcL]`: Source/destination memory address
- `SrcR`: DMA control parameters

**Encoding Details:**
- **Major opcode**: `6..4=3'b000, 3..1=3'b101` (separate from CAS)
- **Sub-opcode**: `14..12=3'b111`
- Reserved fields: `31..25=7'b0000000`, `11..7=5'b00000`

## Encoding Space Allocation

The new instructions use previously unused encoding space in the atomic/DMA group:

| Group | Encoding (`6..4, 3..1`) | Sub-opcode (`14..12`) | Instructions |
|-------|-------------------------|------------------------|--------------|
| DMA | `000, 101` | `111` | DMA |
| CAS | `001, 101` | `000, 001, 010, 011` | CASB, CASH, CASW, CASD |

This allocation avoids conflicts with existing atomic instructions:
- LR.*: `14..12=000` (in `6..4=000` group)
- SC.*: `14..12=001` (in `6..4=000` group)
- LW.*: `14..12=010` (in `6..4=000` group)
- LD.*: `14..12=100` (in `6..4=000` group)
- SD.*: `14..12=101` (in `6..4=000` group)
- SWAP*: `14..12=110` (in `6..4=000` group)

## Use Cases

### Lock-Free Data Structures
```assembly
retry:
  ld [lock_addr], ->x5          # Load current value
  casw.aqrl [lock_addr], x0, x5, ->x6  # Try to acquire (compare 0, swap thread_id)
  b.ne x6, x0, retry            # Retry if not zero
  # Critical section
  sw [lock_addr], x0            # Release lock
```

### Reference Counting
```assembly
incr_refcount:
retry:
  ld [refcount], ->x10
  addi x10, 1, ->x11            # Increment
  casd.aq [refcount], x10, x11, ->x12
  b.ne x10, x12, retry          # Retry if value changed
```

### DMA Transfer Initiation
```assembly
  # Setup DMA parameters in SrcR
  ori x6, DMA_CTRL, ->x6        # Control: direction, size, mode
  dma [x5], x6                  # Initiate DMA from address [x5]
```

## Comparison with 48-bit HL.CAS*

| Feature | 32-bit CAS | 48-bit HL.CAS* |
|---------|------------|----------------|
| **Instruction length** | 32 bits | 48 bits (16-bit prefix + 32-bit main) |
| **Register operands** | 4 independent | 4 independent |
| **Memory ordering** | aq, rl, aqrl | aq, rl, f, aqrl, aqf, rlf, aqrlf |
| **Far flag support** | ❌ No | ✅ Yes |
| **Code density** | Higher (shorter) | Lower (longer) |
| **Use case** | Local cache operations | Remote cache / distributed systems |

**Recommendation:**
- Use **32-bit CAS** for typical single-node synchronization
- Use **48-bit HL.CAS*** when far flag is required for remote cache coherence

## Modified Files

### Core Definition Files
1. `isa/v0.56/opcodes/lx_32.opc` — Added CASB, CASH, CASW, CASD, DMA definitions
2. `isa/v0.56/meta.json` — Updated notes to document new instructions
3. `isa/v0.56/linxisa-v0.56.json` — Recompiled instruction catalog (auto-generated)

### Tool Updates
4. `tools/isa/gen_instruction_fragments.py` — Updated CAS description generation for 32-bit variants

### Documentation Updates
5. `docs/isa/blockIntro/sys_block/atomic.md` — Uncommented and updated CAS section
6. `docs/isa/blockIntro/sys_block/instlist.md` — Added CAS and DMA to instruction list
7. `docs/change_log/update_v0.56_cas_dma.md` — This document

## Validation

All changes have been validated:
- ✅ Encoding conflict check passed (`validate_spec.py`)
- ✅ Instruction catalog compiled successfully (`build_golden.py`)
- ✅ JSON spec contains all 5 new instructions
- ✅ No conflicts with existing atomic, DMA, or other instruction groups

## Next Steps

For projects requiring these instructions:
1. Update assembler to recognize CASB/CASH/CASW/CASD/DMA mnemonics
2. Update disassembler with new opcode patterns
3. Implement hardware decode logic for `6..4=001, 3..1=101` group
4. Add simulator support for CAS and DMA semantics
5. Update compiler intrinsics for atomic operations

## References

- [Atomic Operations Documentation](../isa/blockIntro/sys_block/atomic.md)
- [System Block Instruction List](../isa/blockIntro/sys_block/instlist.md)
- [Encoding Space Analysis](../isa/encoding.md)
- [v0.50 Update Log](update_v0.50.md) — Previous atomic instruction enhancements
