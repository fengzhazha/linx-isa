# 编译与运行手册

本文档介绍在异构模式下，将 LinxISA / Block ISA 视作 device，把任务 offload 到设备侧执行时的编译、链接与运行方式。

> 建议按“kernel 标注 → Host 编译 → Host 运行 → Device 编译 → 链接 → 运行”的顺序阅读。

## 使用前提

- 需要明确哪些函数会作为 kernel 卸载到 Block ISA 侧。
- 需要同时准备 host 可执行文件与 device 可重定位文件两条产物链。
- 需要通过 runtime 信息把 host 观测到的调用/全局变量信息传递给 device 重定位工具。

## kernel 标注

- 将需要卸载到 Block ISA model 运行的函数标记为 `linx_kernel`。
- 同时使用 `noinline`，避免 host 编译阶段把 kernel 直接内联消解。
- 当前 kernel 函数的主要限制：
  1. 参数类型不能是浮点类型。
  2. 参数和返回值宽度不超过 64 bit。
  3. kernel 及其被调用函数中不能直接调用系统库函数。
  4. kernel 及其被调用函数中不能通过函数指针做间接调用。

```c
#include <stdio.h>

int arr[10] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
int brr[10] = {10, 9, 8, 7, 6, 5, 4, 3, 2, 1};

int __attribute__((linx_kernel, noinline)) foo(int n) {
  int i, x, y;
  int sum = 0;

  for (i = 0; i < n; i++) {
    x = arr[i];
    y = brr[i];
    if (x > y) {
      sum = sum + x - 1;
    } else {
      sum = y + 1;
    }
  }
  return sum;
}

int main() {
  int succ = 1;
  int res = foo(10);

  printf("%d\n", res);

  if (res != 42) {
    succ = 0;
  }

  if (succ)
    printf("Test PASSED\n");
  else
    printf("Test FAILED\n");

  return 0;
}
```

以上示例中，`foo` 函数会被识别为 device 侧 kernel。

## Host 编译

host 编译器在编译 kernel 函数时，会在 kernel 中插入 Block ISA 模型接口与 runtime。以
X86 作为 host 时，程序运行到 kernel 函数会从 host 切换到 Block ISA model。
runtime 用于记录 kernel 调用的函数与使用的全局变量信息。host 侧编译方式如下：

- clone 构建 LLVM 编译器：

  ```shell
  git clone -b dev_host_compilation ssh://git@codehub-dg-y.huawei.com:2222/linx/ISA-Codesign/BlockISA/linx-llvm.git
  ```

- clone 构建 Block ISA model 仓：

  ```shell
  git clone -b master ssh://git@codehub-dg-y.huawei.com:2222/Graphflow/BlockISA.git
  ```

- 使用以上 LLVM 编译器编译 host 代码，并链接 Block ISA 模型动态库：

  ```shell
  clang xxx.c -o a.out -L ${model_path}/BlockISA/lib -lfunc_model -lruntime -L/usr/lib64 -lelf -O2 -flinx-instrument
  ```

- 如果编译过程提示以下 warning：

  ```shell
  warning: private global variable xxx is used in kernel function.
  ```

- 以上 warning 产生，是因为 kernel 函数中存在常量字符串。目前 Block ISA 有 gcc 和
  llvm 两条工具链，两条工具链对常量字符串的命名可能不同。若 llvm 编译器将常量字符串
  定义为全局变量，命名为 `a.str`，而 gcc 编译器可能会将该字符串定义为 `b.str`。
  后续处理全局变量时，host 和 device 两侧就无法把这个全局变量对应起来。如果 host 和
  device 都使用 llvm 编译器，可以忽略该 warning；如果 host 使用 llvm、device 使用 gcc，
  则需要在源码中把该字符串显式定义为全局变量再使用。

## Host 运行

host 侧编译链接通过之后，需要在 host 侧运行一次，以获取 kernel 执行期间调用的函数及
全局变量地址信息。runtime 会把这些信息记录到 `linx_runtime_info.json`。以上述示例为例，
先通过环境变量指定 host 可执行文件完全运行在 host machine，然后再执行：

```shell
export BISA_MODEL_RUN=0
./a.out
```

运行结束后，将在执行目录下生成 `linx_runtime_info.json` 文件。

## Device 编译

Device（Block ISA）侧与普通编译流程的差异在于：生成可重定位文件（`.o`）之后，还需要
根据 host runtime 信息修改 Block ISA 可重定位文件中的全局变量地址。因此 Device 侧流程为：

### 编译

使用 Block ISA llvm 编译器将源码编译为 `.o` 文件：

```shell
${compiler_path}/bin/clang a.c b.c -O2 -c --target=linx64 -march=linx64im -mabi=lp64 -fno-jump-tables
```

使用 Block ISA gcc 编译器将源码编译为 `.o` 文件：

```shell
${compiler_path}/linx64-unknown-elf/bin/linx64-unknown-elf-gcc -O2 a.c b.c -fno-section-anchors -c -mcmodel=medlow
```

### 全局变量地址调整

使用工具将 Block ISA 可重定位文件中的全局变量地址修改为 host 可执行文件中对应全局变量的地址。
工具位于 `BlockISA/scripts/reloc_globals`：

```shell
${model_path}/BlockISA/scripts/reloc_globals/reloc_globals --runtime linx_runtime_info.json --device a.o b.o --debug
```

选项说明：

- `--runtime` 指定 host 侧输入的 runtime 信息
- `--device` 指定 device 侧的可重定位文件，可以指定 1-n 个输入文件
- `--debug` 输出中间调试信息
- `--help` 输出帮助信息

若 Block ISA 可重定位文件中使用了全局变量，`reloc_globals` 会把全局变量替换为 host
可执行文件中对应的地址并写回原文件；若没有使用全局变量则不做修改。

此外，异构模式下只有 kernel 相关代码（kernel 本身及其被调用函数）运行在 Block ISA 模型上，
其他非 kernel 代码并不会被模型执行。因此，在处理 device 侧输入 `.o` 文件时，如果存在未定义符号，
工具会通过 runtime 信息判断：

- 若未定义符号在 host 侧 runtime 信息中不存在，则自动生成一个未定义符号的定义。
- 若未定义符号在 host 侧 runtime 信息中被使用，则报错并提示补全该符号定义。

### 链接

通过 gcc 编译器将以上修改后的可重定位文件链接为 Block ISA 可执行文件：

```shell
${compiler_path}/linx64-unknown-elf/bin/linx64-unknown-elf-gcc -O2 a.o b.o -o bisa_kernel.o
```

通过 llvm 编译器将以上修改后的可重定位文件链接为 Block ISA 可执行文件：

```shell
${compiler_path}/bin/clang -O2 a.o b.o -o bisa_kernel.o --target=linx64 -march=linx64im -mabi=lp64
```

### 运行

执行 host 侧可执行文件，运行到 kernel 函数时，Block ISA 模型会读取 Block ISA 可执行文件并执行 kernel；
除 kernel 外，其余代码仍在 host 上运行。

```shell
# 设置 kernel 函数运行在 Block ISA 模型上
unset BISA_MODEL_RUN
./a.out
```

## Python 依赖库（非必须）

> 只有在调试 `reloc_globals` 工具或直接运行源码时，才需要关注本节。

Block ISA 重定位文件中全局变量地址调整工具使用 python3 和
[LIEF](https://lief-project.github.io/) 开发，其中 LIEF 用于读写二进制文件。
`reloc_globals.py` 源码位于 `BlockISA/scripts/reloc_globals`。

- 安装 LIEF：

  ```shell
  git clone https://github.com/lief-project/LIEF.git
  cd LIEF
  python3 setup.py install
  ```

  > 需修改一处 bug

- 运行 `reloc_globals.py`

  ```shell
  python3 ${model_path}/BlockISA/scripts/reloc_globals/reloc_globals.py --host a.out --device a.o b.o --debug
  ```
