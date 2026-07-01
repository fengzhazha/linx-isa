# LinxISA Specification

`isa/` is the canonical specification root for the public LinxISA repository.

## Canonical Artifacts

- Latest profile package: `isa/v0.57/`
- Latest changelog: `isa/v0.57/CHANGELOG.md`
- Previous generated catalog components: `isa/v0.56/{encoding,opcodes,registers,state,meta.json}`
- Previous compiled catalog: `isa/v0.56/linxisa-v0.56.json`
- Historical profiles: retained as the repository's versioned history and not used as the live contract
- Generated codec tables: `isa/generated/codecs/`
- Sail model + coverage assets: `isa/sail/`

## Build + Validate

```bash
python3 tools/isa/check_pto_v057_encoding.py --spec isa/v0.57/state/pto_encoding.json
python3 tools/isa/check_pto_v057_downstream.py --strict
```

## Downstream Consumption

Compiler, emulator, benchmark, model, and TileOP API integration MUST consume
the v0.57 block definition and PTO encoding map to avoid decode/semantic drift.

`isa/v0.57/state/downstream_migration.json` tracks the benchmark, TileOP API,
LLVM, QEMU, tools/model, pyCircuit, PTOAS, and GFSIM deltas for the current
profile.

See also:

- `isa/generated/codecs/README.md`
