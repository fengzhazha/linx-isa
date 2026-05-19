# 灵犀 ISA 导航

<div class="landing-hero">
  <div class="landing-eyebrow">ISA Guide</div>
  <h2>主手册层级与精确附录的分界面</h2>
  <p>
    本页把当前公开 ISA 文档拆成两层：一层是供连续阅读的主手册层级，
    一层是供按助记符、编码和分组精确检索的附录参考。
  </p>
</div>

## 主手册层级

<div class="quick-links">
  <a class="quick-link-card" href="arch/bisa.md">
    <strong>架构叙事</strong>
    <span>块定义、执行模型、跳转方式、程序序、访问控制环与整体约束。</span>
  </a>
  <a class="quick-link-card" href="register/common/intro.md">
    <strong>架构状态</strong>
    <span>GGPR、SSR、Tile、BPC 与两层执行状态的统一说明。</span>
  </a>
  <a class="quick-link-card" href="datatype/intro.md">
    <strong>数据类型</strong>
    <span>浮点、整数、微缩放与低精度格式族的入口页。</span>
  </a>
  <a class="quick-link-card" href="instset/baseInstrs.md">
    <strong>指令家族</strong>
    <span>基础、压缩、标准、半长、超长、向量与张量指令集入口。</span>
  </a>
  <a class="quick-link-card" href="blockIntro/std_block/intro.md">
    <strong>块类型介绍</strong>
    <span>标量、向量、访存、矩阵、模板和系统调用块的组织方式。</span>
  </a>
  <a class="quick-link-card" href="../compiler/manuals.md">
    <strong>编程手册</strong>
    <span>把 ISA 视为 device 时的编译、链接、运行和 runtime 工作流。</span>
  </a>
</div>

## 精确附录参考

<div class="section-grid">
  <div class="section-card">
    <h3><a href="encoding.md">编码格式</a></h3>
    <p>查看指令长度、解码格式、编码空间和示例编码图。</p>
  </div>
  <div class="section-card">
    <h3><a href="groups/index.md">分组索引</a></h3>
    <p>按功能分组浏览加载/存储、ALU、浮点、系统、向量等页面。</p>
  </div>
  <div class="section-card">
    <h3><a href="instructions/index.md">指令 A-Z</a></h3>
    <p>按助记符做逐条查询，适合精确检索单条指令。</p>
  </div>
</div>

## 建议阅读顺序

1. 从 [总体架构](arch/bisa.md) 开始，建立块指令与两层执行的整体模型。
2. 阅读 [架构状态](register/common/intro.md) 与 [数据类型](datatype/intro.md)，理解状态与操作数基础。
3. 阅读 [指令家族](instset/baseInstrs.md) 与 [块类型介绍](blockIntro/std_block/intro.md)，理解 ISA 的组织方式。
4. 需要编码或单条指令时，切换到 [编码格式](encoding.md)、[分组索引](groups/index.md) 或 [指令 A-Z](instructions/index.md)。

## 直达入口

<ul class="doc-pills">
  <li><a href="arch/execute.md">执行模型</a></li>
  <li><a href="arch/constraints.md">约束</a></li>
  <li><a href="register/ssr/ssrintro.md">系统寄存器</a></li>
  <li><a href="datatype/HiF_SCALE.md">HiF Microscaling</a></li>
  <li><a href="encoding.md">编码格式</a></li>
  <li><a href="instructions/index.md">指令附录</a></li>
</ul>
