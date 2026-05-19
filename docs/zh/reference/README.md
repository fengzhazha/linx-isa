# 参考与示例

本节收纳适合“精确查询”的资料，而不是连续阅读的主手册叙事。

## 内容结构

<div class="section-grid">
  <div class="section-card">
    <h3><a href="examples/README.md">样例总览</a></h3>
    <p>进入 v0.56 规范样例包，查看样例组织方式与来源说明。</p>
  </div>
  <div class="section-card">
    <h3><a href="encoding_space_report.md">编码空间分析</a></h3>
    <p>查看指令编码空间分配、冲突分析与版本演进背景。</p>
  </div>
  <div class="section-card">
    <h3><a href="linxisa-assembly-agent-guide.md">汇编代理指南</a></h3>
    <p>聚焦块 ISA 汇编、ABI、展开、信号与上下文切换模式。</p>
  </div>
  <div class="section-card">
    <h3><a href="linxisa-call-ret-contract.md">Call/Ret 合同</a></h3>
    <p>规范调用、返回、尾调用与融合块头的行为边界。</p>
  </div>
</div>

## 推荐使用方式

- 想看可运行/可复用的例子时，从 [样例总览](examples/README.md) 开始。
- 想确认某条编码或某类格式是否占用冲突时，进入 [编码空间分析](encoding_space_report.md)。
- 想处理汇编生成、代理补丁或 ABI 相关问题时，先看
  [汇编代理指南](linxisa-assembly-agent-guide.md) 和
  [Call/Ret 合同](linxisa-call-ret-contract.md)。
