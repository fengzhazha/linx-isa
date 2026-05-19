# 指令编码格式

> **ISA 版本：** v0.56.2  
> **对应手册章节：** 第 03 章（编码与格式）

本页说明 LinxISA v0.56 的指令长度、主要解码布局、编码空间，以及几个代表性指令的编码示意图。
所有示意图均由 `isa/v0.56/linxisa-v0.56.json` 重新生成，和当前公开规范保持一致。

## 指令长度

LinxISA 当前公开文档使用小端字节序，并围绕半字（16-bit）对齐组织四种长度：

| 命名空间 | 格式 | 位宽 | 结构 | 代表指令 |
|---|---|---:|---|---|
| `C.` | C16 | 16 | 单个 16-bit 指令体 | `C.ADD`、`C.LD`、`C.BSTART.FP` |
| 基础标量 | LX32 | 32 | 单个 32-bit 指令体 | `ADD`、`LD`、`BSTART CALL` |
| `HL.` | HL48 | 48 | 16-bit 前缀 + 32-bit 主体 | `HL.LDI`、`HL.CASB`、`HL.SETRET` |
| `V.` | V64 | 64 | 32-bit 高位前缀 + 32-bit 主体 | `V.ADD`、`V.FMADD`、`V.DIV` |

> `HL.*` 和 `V.*` 形式都属于“前缀 + 主体”的增强编码；前缀本身不单独构成可执行语义。

## 常见解码布局

### 16-bit（C.）常见布局

| 标签 | 典型字段 |
|---|---|
| `C.Type A` | `SrcL`、`SrcR` |
| `C.Type B` | `SrcL`、`uimm5` |
| `C.Type C` | `SrcL`、`Func` |
| `C.Type D` | `SrcL`、`RegDst` |
| `C.Type E` | `RegDst`、`uimm5` |
| `C.Type F` | `Func`、`uimm5` |
| `C.Type G` | 仅立即数 / 块标记 |
| `C.Type H` | `imm10` |
| `C.Type I` | `imm12` |

### 32-bit 常见布局

| 标签 | 典型字段 |
|---|---|
| `Type A` | `RegDst`、`SrcL`、`SrcR` [、`SrcD`] |
| `Type B` | `RegDst`、`SrcL`、`SrcR` + 小立即数 |
| `Type C` | `SrcL`、`SrcR` + 两个立即数字段 |
| `Type D` | `RegDst`、`SrcL` + `simm` |
| `Type F` | `RegDst`、`SrcL` + `simm` |
| `Type G` | `RegDst` + `simm` |
| `Type H` | `SrcL`、`SrcR` + `simm` |

## 编码空间

| 编码族 | 主要位段 | 槽位数 | 说明 |
|---|---|---:|---|
| C16 | `C16[15:13]` | 8 | 压缩 16-bit 形式 |
| LX32 | `[31:26]` | 64 | 基础 32-bit 指令空间 |
| HL48 | `[47:40]` | 256 | 高级前缀空间 |
| V64 | `[63:58]` | 64 | 向量前缀空间 |

需要完整的无冲突分配视图时，请转到
[编码空间分析](../reference/encoding_space_report.md)。

## 字段颜色图例

![编码图例](wavedrom/encoding_legend.svg)

## 代表性示例

### 32-bit：ADD

![ADD 编码](wavedrom/enc_add.svg)

### 16-bit：C.ADD

![C.ADD 编码](wavedrom/enc_c_add.svg)

### 48-bit：HL.LDI

![HL.LDI 编码](wavedrom/enc_hl_ldi.svg)

### 64-bit：V.ADD

![V.ADD 编码](wavedrom/enc_v_add_parts.svg)

## 相关页面

- [ISA 总索引](index.md)
- [指令 A-Z 附录](instructions/index.md)
- [分组索引](groups/index.md)
- [编码空间分析](../reference/encoding_space_report.md)
