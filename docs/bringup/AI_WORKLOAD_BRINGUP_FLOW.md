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

- `smoke`: Tier 0. AVS PTO/tile smoke plus minimal SuperNPUBench tileop cases.
- `pr`: Tiers 0-1. Adds PTO kernel compile/static checks and basic kernel cases.
- `nightly`: Tiers 0-3. Adds matrix, memory, reduction, accelerator, and DeepSeek/model-oriented cases.
- `full`: Tiers 0-4. Full AI workload matrix.

Use `--tier`, `--kind`, `--case`, and `--limit` to narrow local debugging.
Use `--clang`, `--clangxx`, `--lld`, `--qemu`, `--model-root`, or `--gfsim`
when testing an external lane. The pin lane defaults to in-repo Linx LLVM,
`emulator/qemu/build/qemu-system-linx64`, and
`model/LinxCoreModel/bin/gfsim`.

## Stage Order

1. `source-contract`: validate PTO catalogs, SuperNPUBench manifests, source paths, hashes, and normalized case records.
2. `compiler-contract`: compile with `compiler/llvm/build-linxisa-clang/bin`, produce ELF/object/asm evidence, and run static checks.
3. `qemu-execution`: run compiler-passing executable cases in Linx QEMU and capture logs/digests.
4. `model-build-smoke`: build or locate `model/LinxCoreModel/bin/gfsim`, then run a smoke ELF when available.
5. `linxcoremodel-execution`: run only QEMU-passing ELFs through `gfsim -f <elf>`.
6. `differential-triage`: compare QEMU/model digest evidence when both sides emit it.
7. `fix-packets`: emit bounded agent packets for the first failing owner.
8. `skill-doc-evolution`: write an explicit `skill-evolve` update/no-update closeout.

The runner stops on the first red hard-break stage unless
`--continue-on-fail` is set.

## Case Types

- `avs_pto`: executable AVS direct-boot PTO/tile suites. These produce
  `linx-qemu-tests.elf` through `avs/qemu/run_tests.py` and are model-eligible.
- `supernpu`: SuperNPUBench `compile.all` Makefile cases compiled with
  `PLAT=linx`. These produce SuperNPUBench Linx ELFs and are model-eligible.
- `pto_kernel`: cataloged PTO kernel sources. These currently participate in
  source and compile/static stages; a standalone ELF harness is required before
  they can enter QEMU/model stages individually.

## Owner Classification

The first failing boundary assigns the fix lane:

- `benchmark`: source, manifest, API, or workload normalization failure.
- `compiler`: clang, LLVM backend, MC, link, entry symbol, relocation, or retired-token static failure.
- `emulator`: legal compiler output fails under QEMU.
- `model`: QEMU-passing ELF fails to build, load, decode, execute, or match digest evidence in `gfsim`.
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
