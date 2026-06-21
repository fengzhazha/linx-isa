# AI Workload Bring-up Flow

This is the canonical hard-break loop for maturing LinxISA AI workloads until
QEMU-passing Linx ELFs also run in the C++ `model/LinxCoreModel` target.

Machine-readable flow:

- `docs/bringup/ai_workload_bringup_flow.json`

Runner:

```bash
python3 tools/bringup/run_ai_workload_flow.py --profile smoke --dry-run
python3 tools/bringup/run_ai_workload_flow.py --profile smoke --run-id <run-id>
```

Artifacts are written under:

```text
workloads/generated/<run-id>/ai-bringup/
```

## Profiles

- `smoke`: Tier 0. Bounded AVS PTO parity/tile smoke plus minimal SuperNPUBench tileop cases.
- `pr`: Tiers 0-1. Adds PTO kernel compile/static checks, the full smoke-sized AVS PTO parity maturity suite, and basic kernel cases.
- `nightly`: Tiers 0-3. Adds matrix, memory, reduction, accelerator, and DeepSeek/model-oriented cases.
- `full`: Tiers 0-4. Full AI workload matrix.

Use `--tier`, `--kind`, `--case`, and `--limit` to narrow local debugging.
By default `--case` is a substring filter across case id, suite, and kind.
Prefix the selector with `=` for exact matching, for example
`--case '=supernpu-tileop_api-TAdds'`.
Use `--clang`, `--clangxx`, `--lld`, `--qemu`, `--model-root`, or `--gfsim`
when testing an external lane. The pin lane defaults to in-repo Linx LLVM,
`emulator/qemu/build-linx/qemu-system-linx64`, and
`model/LinxCoreModel/bin/gfsim`.

Timeouts are lane-specific: `--model-build-timeout` gates CMake configure/build
and generated model-smoke ELF compilation, while `--model-timeout` gates
`gfsim -f <elf>` smoke and workload runs. Non-dry runs rebuild
`model/LinxCoreModel/bin/gfsim` unless `--skip-model-build` is passed.

## Stage Order

1. `source-contract`: validate PTO catalogs, SuperNPUBench manifests, source paths, hashes, and normalized case records.
2. `compiler-contract`: compile with `compiler/llvm/build-linxisa-clang/bin`, produce ELF/object/asm evidence, and run static checks.
3. `qemu-execution`: run compiler-passing executable cases in Linx QEMU and capture logs/digests.
4. `model-build-smoke`: rebuild or locate `model/LinxCoreModel/bin/gfsim`, then run a known tiny Linx smoke ELF. By default the runner generates `cases/_model/linx-model-smoke.{cpp,ld,elf}`; `--model-smoke-elf` can override it.
5. `linxcoremodel-execution`: run only QEMU-passing ELFs through `gfsim -f <elf>`.
   On model failures, the runner parses the `gfsim` log for finisher writes,
   assertion text, and the latest periodic BROB head progress so the failure
   packet names the repeated BPC or terminal marker directly.
6. `differential-triage`: compare QEMU/model digest evidence when both sides emit it.
7. `fix-packets`: emit bounded agent packets for the first failing owner.
8. `skill-doc-evolution`: write an explicit `skill-evolve` update/no-update closeout.

The runner stops on the first red hard-break stage unless
`--continue-on-fail` is set.

## Case Types

- `avs_pto`: executable AVS direct-boot PTO/tile suites. These produce
  `linx-qemu-tests.elf` through `avs/qemu/run_tests.py` and are model-eligible.
  Tier-0 PTO parity is the bounded `avs-pto-parity-smoke` case, which passes
  `-DPTO_PARITY_TLOAD_STORE_ONLY=1` through the AVS extra-cflag hook and runs
  only the `tload_store` digest path. The full smoke-sized parity sequence remains
  `avs-pto-parity` in Tier 1 so long-running model behavior still emits a
  model-owned maturity packet instead of hiding behind the smoke lane.
  Tier-0 tile smoke uses the AVS compile-smoke source override during QEMU
  execution so it exercises the PTO/QEMU/model handoff before the full tile
  runtime source is green. Keep this case-level smoke separate from
  `model-build-smoke`; the global model smoke must remain a generated tiny ELF
  unless `--model-smoke-elf` is explicitly provided.
- `supernpu`: SuperNPUBench `compile.all` Makefile cases compiled with
  `PLAT=linx`. The runner passes a per-case `OBJ_ROOT` under
  `cases/<case>/compiler/supernpu-output/`, links these as direct-boot Linx
  ELFs with `_start` first at `0x10000`, and copies the canonical ELF,
  objdump outputs, raw bin, and linker script into the compiler artifact
  directory for QEMU/model triage. Current direct-boot green tileop cases are
  `MatMul`, `MatMacc`, `test_MatMul`, `test_MatMacc`, `TAdd`, `TAbs`, `TCI`,
  `TCopyIn`, `TCopyOut`, `TCopy`, `TCvt`, `TExpandCol`, `TExpandRow`,
  `TExpandScalar`, `TReshape`, `TTrans`, `TPad`, `TRowMax`, `TRowMaxExpand`,
  `TRowSum`, `TRowSumExpand`, `TSub`, `TSubs`, `TAdd_mask`, `TAdds`, `TDiv`,
  `TDivs`, `TExp`, `TRem`, `TRecip`, `TSqrt`, `TMul`, `TMuls`, `TMax`, `TMaxs`,
  `TAnd`, `TOr`, and `TCmp`; keep future promotions similarly bounded and
  prove each exact case through QEMU and `gfsim -f <elf>`. `MatMacc` is currently a
  bounded `4x4` int64 row-major multiply-accumulate smoke; col-major MatMacc
  has QEMU-pass/model-fail evidence and remains a model-lane maturity packet.
  `test_MatMul` is currently a bounded `4x4` int64 row-major MATMUL smoke;
  its original TileLeft/TileRight/TileAcc plus TCVT float path remains deferred
  until the Linx direct-boot model lane supports that runtime contract.
  `test_MatMacc` is currently a bounded `4x4` int64 row-major MATMUL+MATMACC
  smoke; its original TileLeft/TileRight/TileAcc plus TCVT float path remains
  deferred on the same model-lane runtime contract. `MatMul_e4m3` remains a
  benchmark-owned maturity packet: keep the original FP8 e4m3 conversion,
  TileLeft/TileRight inputs, TileAcc output, and vector-kernel conversion
  contract intact until the Linx direct-boot lane has real boxed/ACC/FP8 support.
  Do not replace it with the existing int64 `MatMul` smoke. `TSqrt` is currently a
  bounded `4x4` int64 perfect-square direct-boot smoke; broader integer and
  floating-point sqrt remain deferred until the model lane has matching
  evidence. `TExp` is currently a bounded `4x4` int64 rounded-exp
  direct-boot smoke using a comparison ladder; float/half exponential and
  compiler-generated constant-table paths remain deferred until the model lane
  has matching evidence.
- `pto_kernel`: cataloged PTO kernel sources. These currently participate in
  source and compile/static stages; a standalone ELF harness is required before
  they can enter QEMU/model stages individually.

## Owner Classification

The first failing boundary assigns the fix lane:

- `benchmark`: source, manifest, API, or workload normalization failure.
  SuperNPUBench compiler-stage logs are still benchmark-owned when they show a
  missing Linx tile API implementation such as `*_Impl`, unsupported Linx tile
  runtime contracts such as vector-kernel syntax or boxed layouts, or
  direct-boot source paths that still depend on host libc/soft-float symbols.
- `compiler`: clang, LLVM backend, MC, link, entry symbol, relocation, or retired-token static failure.
- `emulator`: legal compiler output fails under QEMU.
- `model`: QEMU-passing ELF fails to build, load, decode, execute, or match digest evidence in `gfsim`.
  For scalar or vector select divergence around `csel`/`psel`, the model must
  match the LLVM/QEMU contract: `SrcP != 0` selects `SrcR`; `SrcP == 0` selects
  `SrcL`.
- `docs-skills`: the run exposes a reusable contract, command, or triage rule not covered by docs/skills.

Each failed case gets a JSON packet under `fix-packets/` with owner, evidence,
repro command, logs, artifacts, and expected next boundary.

## Required Evidence

Every run emits:

- `manifest.json`: tool paths, submodule SHAs, profile/tiers, selected cases.
- `report.json`: per-stage and per-case machine-readable status.
- `summary.md`: human triage table.
- `skill_evolution.{json,md}`: explicit skill closeout.
- `cases/<case>/...`: source hashes, compile logs, ELF/object/asm, objdump,
  optional raw bin, QEMU log, model log, and fix packet links when relevant.
  Model execution rows also carry parsed diagnostics when available:
  `finisher_value`, `finisher_status`, `assertion`, `last_brob_bpc`,
  `last_retired_blocks`, and `last_brob_head`.
- `cases/_model/`: CMake logs plus generated model-smoke source, linker script,
  ELF, compile log, and `gfsim` smoke transcript.
