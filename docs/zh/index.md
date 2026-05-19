# 灵犀指令集文档站点

<div class="landing-hero">
  <div class="landing-eyebrow">LinxISA Public Docs</div>
  <h2>面向公开阅读的中文主站</h2>
  <p>
    当前 GitHub Pages 站点以中文文档树作为主入口，覆盖架构背景、ISA 手册层级、
    架构合同、编译与 bring-up 资料，以及保留用于精确检索的 ISA 附录页面。
  </p>
  <div class="hero-meta">
    <span>当前公开版本：v0.56.x</span>
    <span>规范来源：architecture/ + isa/</span>
    <span>站点入口：GitHub Pages 根域名</span>
  </div>
</div>

## 快速入口

<div class="quick-links">
  <a class="quick-link-card" href="background/index.md">
    <strong>设计背景</strong>
    <span>先理解块指令为什么存在、它解决什么问题，以及 LinxISA 与传统 CPU/GPU ISA 的差异。</span>
  </a>
  <a class="quick-link-card" href="isa/index.md">
    <strong>ISA 导航</strong>
    <span>从架构叙事、状态模型、数据类型、指令家族到块类型介绍的统一入口。</span>
  </a>
  <a class="quick-link-card" href="architecture/README.md">
    <strong>架构合同</strong>
    <span>查看 v0.56 架构合同页、加固策略和 AsciiDoc ISA 手册等规范性材料。</span>
  </a>
  <a class="quick-link-card" href="compiler/manuals.md">
    <strong>编译与工具</strong>
    <span>进入 host/device 工作流、kernel offload、链接、运行和工具链使用说明。</span>
  </a>
  <a class="quick-link-card" href="reference/README.md">
    <strong>参考与示例</strong>
    <span>汇总样例、编码空间分析、汇编代理指南和 call/ret 合同。</span>
  </a>
  <a class="quick-link-card" href="bringup/README.md">
    <strong>Bring-up 与验证</strong>
    <span>浏览当前 bring-up 进展、验证 gate、快速开始和交叉栈状态说明。</span>
  </a>
</div>

## 建议阅读顺序

1. 从 [设计背景](background/index.md) 建立整体心智模型。
2. 进入 [ISA 导航页](isa/index.md)，按“架构叙事 → 状态模型 → 数据类型 → 指令家族”的顺序阅读。
3. 需要规范性约束时，回到 [架构合同总览](architecture/README.md) 和
   [v0.56 合同页](architecture/v0.56-architecture-contract.md)。
4. 需要工具链与运行方式时，阅读 [编程手册](compiler/manuals.md) 及其相关工具页面。
5. 需要精确检索指令、编码或样例时，使用 [参考总览](reference/README.md) 和
   [ISA 附录索引](isa/instructions/index.md)。

## 文档分层

| 层级 | 作用 | 首选入口 |
|---|---|---|
| 背景与叙事 | 为什么这样设计、整体架构是什么 | [background/index.md](background/index.md) |
| ISA 主手册层级 | 架构、状态、类型、块类型、指令家族 | [isa/index.md](isa/index.md) |
| 规范性合同 | v0.56 对外行为边界、英文手册源 | [architecture/README.md](architecture/README.md) |
| 工具与 bring-up | 编译、运行、验证、生态 bring-up | [compiler/manuals.md](compiler/manuals.md), [bringup/README.md](bringup/README.md) |
| 精确参考 | 编码、示例、附录、代理指南 | [reference/README.md](reference/README.md) |

## 常用文档面

<ul class="doc-pills">
  <li><a href="isa/arch/bisa.md">总体架构</a></li>
  <li><a href="isa/register/common/intro.md">架构状态</a></li>
  <li><a href="isa/datatype/intro.md">数据类型</a></li>
  <li><a href="isa/encoding.md">指令编码</a></li>
  <li><a href="reference/examples/v0.56/README.md">v0.56 示例包</a></li>
  <li><a href="releases/v0.56.2.md">当前发布说明</a></li>
</ul>
