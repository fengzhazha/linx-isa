# Skill Evolution Summary: AI add_custom Harness Promotion

- Generated UTC: `2026-06-21T19:44:55Z`
- Skills SHA: `00e08019d2585c8c6b676e94b1c633c41519e5f2`
- Updated skill: `linx-superproject`

## Decision

`skill-evolve: updated linx-superproject (pto-kernel-add_custom now has a proven direct-boot smoke harness and QEMU-to-gfsim evidence)`

## Evidence

- `ai-debug-add-custom-harness-02`: `pto-kernel-add_custom` passed source contract, compiler contract, QEMU execution, model-build smoke, and `gfsim -f <elf>`.
- The 30-second debug timeout was too tight for the 1024-element scalar smoke loop; the runner default model timeout remains sufficient.
- `add_custom` uses a harness-local freestanding `__addsf3` helper scoped to positive integer-valued smoke inputs and must not be treated as a full compiler-rt replacement.

## Validation

- `python3 -m py_compile tools/bringup/run_ai_workload_flow.py`
- `python3 /Users/zhoubot/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/zhoubot/linx-isa/skills/linx-skills/linx-superproject`
- `python3 /Users/zhoubot/linx-isa/skills/linx-skills/scripts/check_skill_change_scope.py --repo-root /Users/zhoubot/linx-isa/skills/linx-skills --base origin/main`
- `bash /Users/zhoubot/linx-isa/skills/linx-skills/scripts/install_canonical_skills.sh`
