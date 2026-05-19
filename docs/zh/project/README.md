# 项目与治理

本节收录仓库导航契约、维护流程和超级项目治理资料。

## 首选入口

<div class="section-grid">
  <div class="section-card">
    <h3><a href="navigation.md">导航契约</a></h3>
    <p>定义允许路径、规范目的地、禁止路径和子模块更新策略。</p>
  </div>
  <div class="section-card">
    <h3><a href="repository-flow.md">仓库流程</a></h3>
    <p>说明贡献、分支、发布与对齐工作的常规执行方式。</p>
  </div>
  <div class="section-card">
    <h3><a href="superproject-bringup-methodology.md">Bring-up 方法论</a></h3>
    <p>面向代理和维护者的超级项目 bring-up 操作方法。</p>
  </div>
  <div class="section-card">
    <h3><a href="maintainer-repin-checklist.md">Repin 清单</a></h3>
    <p>子模块 repin 前后的检查点与风险控制要点。</p>
  </div>
</div>

## 其他资料

- [omx-linxisa-playbook.md](omx-linxisa-playbook.md) — OMX 操作手册
- [omx-linxisa-prompt-templates.md](omx-linxisa-prompt-templates.md) — 可复用提示模板
- [new-agent-sop.md](new-agent-sop.md) — 新代理进入仓库时的简明 SOP
- [linxisa-superproject-methodology-zh.pdf](linxisa-superproject-methodology-zh.pdf) — 中文方法论 PDF
- [superproject-whitepaper-zh.pdf](superproject-whitepaper-zh.pdf) — 中文白皮书 PDF

## 快速参考

| 任务 | 规范位置 |
|---|---|
| 运行时测试 | `avs/qemu/` |
| 编译测试 | `avs/compiler/linx-llvm/tests/` |
| 独立式 libc | `avs/runtime/freestanding/` |
| PTO kernel 头文件 | `workloads/pto_kernels/include/` |
| 公开样例 | `docs/reference/examples/v0.56/` |

在提交前，始终运行：

```bash
bash tools/ci/check_repo_layout.sh
```
