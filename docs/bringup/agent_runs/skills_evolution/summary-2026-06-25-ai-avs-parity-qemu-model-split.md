# AI AVS Parity QEMU/Model Lane Split

- Generated (UTC): `2026-06-25T08:32:21Z`
- Skills submodule: `skills/linx-skills`
- Skills SHA: `c42152d9883c3743ecc28744fe9a616c16dda47b`
- Updated skills: `linx-model`, `linx-superproject`

## Reason

The full `avs-pto-parity` row proves source, compiler, and QEMU parity for the
current smoke-sized AVS PTO sequence, but current model evidence reaches
`flash_attention_softmax` and then times out in `flash_attention_demo_f32` at
BROB BPC `0x17eaa` inside scalar soft-float normalization. Treating that row as
model-eligible in the Tier-1 PR lane turns a known Tier-4 closure target into a
recurring PR hard break.

The reusable boundary is now explicit:

- `avs-pto-parity`: Tier 1 QEMU parity maturity row, not model-eligible.
- `avs-pto-parity-full-model`: Tier 4 full-row LinxCoreModel closure target.
- Model-green PR coverage remains on the prefix micro-profile rows.

## Evidence

- Run: `ai-avs-parity-qemu-row-actual-01`, 1 selected, source/compile/QEMU pass.
- Model stage result: `model-build-smoke` and `linxcoremodel-execution` are
  `not_applicable` for the QEMU-only row.
- Final full-model dry-run: `ai-avs-parity-full-model-dry-02`, selected case is
  Tier 4 and model-eligible.
- Runner validation: `python3 -m py_compile tools/bringup/run_ai_workload_flow.py tools/bringup/test_run_ai_workload_flow.py`.
- Unit validation: `python3 -m unittest tools.bringup.test_run_ai_workload_flow`.
- Flow schema validation: `python3 -m json.tool docs/bringup/ai_workload_bringup_flow.json`.
- Layout validation: `bash tools/ci/check_repo_layout.sh`.
- Skill validation: `python3 /Users/zhoubot/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/zhoubot/linx-isa/skills/linx-skills/linx-model`.
- Skill validation: `python3 /Users/zhoubot/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/zhoubot/linx-isa/skills/linx-skills/linx-superproject`.
- Skill scope guard: `python3 skills/linx-skills/scripts/check_skill_change_scope.py --repo-root skills/linx-skills --base origin/main`.
- Skill install: `bash /Users/zhoubot/linx-isa/skills/linx-skills/scripts/install_canonical_skills.sh`.

## Closeout

- skill-evolve: updated `linx-model` and `linx-superproject` with the
  `avs-pto-parity` Tier-1 QEMU parity / `avs-pto-parity-full-model` Tier-4
  LinxCoreModel closure split.
