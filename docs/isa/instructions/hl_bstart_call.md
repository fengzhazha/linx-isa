# HL.BSTART CALL

<div class="insn-header">

<span class="badge-48">48-bit HL.</span> **Group:** <a href="../groups/bstart.md">BSTART</a> &nbsp;|&nbsp;
<span class="ch-tag ch-tag-04">Ch 04</span>
&nbsp; <strong>Block ISA — Block-structured Control Flow</strong> &nbsp;|&nbsp;
**Length:** <code>48</code> &nbsp;|&nbsp; **Decode:** <code>—</code>

</div>

## Assembly Syntax

- `HL.BSTART.CALL, <br_label>, <rt_label>, -> ra`

## Encoding

<div class="enc-diagram">

<figure>
<img src="../wavedrom/enc_hl_bstart_call.svg" alt="HL.BSTART CALL encoding" width="100%" />
<figcaption>48-bit encoding: 16-bit prefix + 32-bit main instruction. MSB is on the left, LSB on the right.</figcaption>
</figure>

</div>

## Description

`HL.BSTART.CALL` is the 48-bit call form of the block split marker. It terminates the current block, initiates a new block, and stores the return address (the fall-through PC of the current block) into register `x10`/`ra`. At commit, the block engine unconditionally jumps to the `br_label` target encoded as a signed 25-bit immediate left-shifted by 1 (`PC + (simm25 << 1)`). The 48-bit encoding provides a much larger PC-relative offset range than the 32-bit `BSTART.CALL` form.

The 48-bit form consists of a 16-bit prefix (`HL.`) concatenated with the 32-bit `BSTART.CALL` main instruction. The prefix augments the instruction space and provides the upper bits of the extended immediate.

**Contrast with other HL.BSTART forms:**

| Form | Xfer kind | Taken? | Return addr? | Description |
|------|-----------|--------|-------------|-------------|
| `HL.BSTART.SYS` | `SYS` | N/A | No | System block call (XB interface) |
| `HL.BSTART.STD` | `STD` | N/A | No | Standard block start (prefix form) |
| `HL.BSTART.FP` | `FP` | N/A | No | Floating-point block start |
| `HL.BSTART.CALL` | `CALL` | Always taken | Yes (`x10/ra`) | Unconditional call with link register |

## Pseudocode (informative)

```c
// At decode: compute call target from simm25 immediate (HL form)
target = PC + ZeroExtend(simm25 << 1);

// At commit:
x10 = next_bpc;   // write return address to link register (x10 = ra)
pc = target;       // jump to call target
ResetBARG();       // reset block argument register for new block
```

## Encoding Notes

The 48-bit `HL.BSTART.CALL` consists of a 16-bit prefix concatenated with the 32-bit `BSTART.CALL` main instruction:

| Part | Bits | Field | Value | Description |
|------|------|-------|-------|-------------|
| Prefix | `[47:43]` | `5'b01010` | `5'b01010` | HL prefix opcode |
| Prefix | `[42:38]` | `uimm5` | — | Reserved; must be `5'b00000` |
| Prefix | `[37:36]` | `2'b01` | `2'b01` | Prefix class |
| Prefix | `[35:33]` | `3'b011` | `3'b011` | Block type = STD |
| Prefix | `[32]` | `1'b0` | `1'b0` | Reserved |
| Main | `[31:27]` | `5'b01010` | `5'b01010` | BSTART opcode base |
| Main | `[26:22]` | `uimm5` | — | Reserved; must be `5'b00000` |
| Main | `[21:20]` | `2'b01` | `2'b01` | Transfer kind class |
| Main | `[19:17]` | `3'b011` | `3'b011` | Block type = STD |
| Main | `[16]` | `1'b0` | `1'b0` | Contract kind |
| Main | `[15:4]` | `simm25[11:0]` | — | Lower 12 bits of simm25 |
| Main | `[3:1]` | `3'b001` | `3'b001` | Transfer kind upper bits (`0b0011`) |
| Main | `[0]` | `1'b1` | `1'b1` | HL terminal bit |

**Decode mask:** `(inst_main & 0xf83f0000007f) == 0x501600000011`

The `simm25` immediate spans `[31:7]` of the main instruction, composed of bits `[31:7]` of the main word. The prefix does not contribute additional immediate bits — the `simm25` is carried entirely within the main 32-bit part.

The `uimm5` fields in both prefix (`[42:38]`) and main (`[26:22]`) are reserved; hardware ignores their values in this form.

## Exception and Trap Behavior

If the `br_label` target does not fall on a valid block start boundary, the block engine raises an exception (`EC_CFI_BAD_TARGET`) and traps to the current ACR's exception handler without modifying architectural state.

## Full Catalog Forms

| Assembly | Length | Decode |
|----------|--------|--------|
| `HL.BSTART.CALL, <br_label>, <rt_label>, -> ra` | 48 | `47:43=0b01010, 37:36=0b01, 35:33=0b011, 32=0, 31:27=0b01010, 21:20=0b01, 19:17=0b011, 3:1=0b001, 0=1` |

<div class="insn-nav">

← [BSTART](../groups/bstart.md) &nbsp;&nbsp; [Index](../index.md) &nbsp;&nbsp; [All instructions](index.md) →

</div>
