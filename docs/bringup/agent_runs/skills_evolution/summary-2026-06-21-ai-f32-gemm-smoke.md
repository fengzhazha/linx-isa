# Skill Evolution Summary: AI Float GEMM Smoke Promotion

- Generated UTC: `2026-06-21T20:00:53Z`
- Skills SHA: `e7de9e0c3efc324459b53af280d5c03e8d0a736a`
- Updated skill: `linx-superproject`

## Decision

`skill-evolve: updated linx-superproject (pto-kernel-gemm_basic and pto-kernel-gemm_demo now have proven direct-boot smoke harnesses and QEMU-to-gfsim evidence)`

## Evidence

- `ai-debug-pto-f32-gemm-copy-02`: `pto-kernel-gemm_basic` and `pto-kernel-gemm_demo` passed source contract, compiler contract, QEMU execution, model-build smoke, and `gfsim -f <elf>`.
- `gemm_demo_f32` requires the harness call order `(out, a, b)`; an earlier generic `(lhs, rhs, dst)` call produced QEMU timeout evidence and was corrected before promotion.
- The promoted smokes are float bit-pattern copy-oracles for `PTO_QEMU_SMOKE` branches and do not claim full float TMATMUL/TCVT/TMULS parity.

## Validation

- `python3 -m py_compile tools/bringup/run_ai_workload_flow.py`
- `python3 /Users/zhoubot/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/zhoubot/linx-isa/skills/linx-skills/linx-superproject`
- `python3 /Users/zhoubot/linx-isa/skills/linx-skills/scripts/check_skill_change_scope.py --repo-root /Users/zhoubot/linx-isa/skills/linx-skills --base origin/main`
- `bash /Users/zhoubot/linx-isa/skills/linx-skills/scripts/install_canonical_skills.sh`
