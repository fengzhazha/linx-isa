# AI AVS Parity QEMU/Model Lane Split

- Generated (UTC): `2026-06-25T08:32:21Z`
- Skills submodule: `skills/linx-skills`
- Skills SHA: `75b40426e431a8e688bcba7b45f0703baa09dda3`
- Updated skills: `none`

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

## Closeout

- skill-evolve: no-update. The reusable knowledge was recorded in the runner
  case matrix and bring-up docs; no installed skill command or submodule skill
  text changed in this pass.
