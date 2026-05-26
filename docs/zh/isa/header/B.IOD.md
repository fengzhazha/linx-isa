# B.IOD

## 说明

B.IOD(*Block Input and Output Dependency*)<br>
本指令用于并行块指令中表达对前序指令的依赖以及对后序指令产生屏障作用。

软件可以通过该指令表达并行块指令之间的依赖信息，避免块指令间过度并行化导致执行出错。

## 汇编语法

```asm
    B.IOD DepSrc0, DepSrc1, DepSrc2, ->DepDst
```

## 汇编符号

- **DepSrc0 / DepSrc1 / DepSrc2**：表示本块指令最多可显式记录 3 个前序 D 依赖槽位。未使用的槽位编码为 0。
- **DepDst**：表示本块指令对后序引用该标识的块指令的屏障。

## 编码格式

![B.IOD](../../figs/bitfield/svg/BlockHeader_32bit/B.IOD.svg)

依赖关系表（单个依赖槽位的编码含义）:

| 输入输出编码 | DepSrc  | DepDst  |
|-------------|---------|---------|
| 5'b00000    | 无依赖   | 无输出  |
| 5'b00001    | D#1     | D       |
| 5'b00010    | D#2     | reserve |
| 5'b00011    | D#3     | reserve |
| 5'b00100    | D#4     | reserve |
| 5'b00101    | D#5     | reserve |
| 5'b00110    | D#6     | reserve |
| 5'b00111    | D#7     | reserve |
| 5'b01000    | D#8     | reserve |
| others      | reserve | reserve |

## 汇编示例

当前 v0.56 golden 将 `B.IOD` 建模为 3 个显式依赖输入槽位加 1 个输出屏障槽位。
高层块语法如果只表达单个 `D#n` 依赖，应在编码时映射到 `DepSrc0`，其余依赖槽位置 0。
