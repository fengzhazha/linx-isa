# LinxISA Specification

`isa/` is the canonical specification root for the public LinxISA repository.

## Canonical Artifacts

- Canonical components: `isa/v0.56/{encoding,opcodes,registers,state,meta.json}`
- Compiled catalog: `isa/v0.56/linxisa-v0.56.json`
- Proposed v0.57 profile: `isa/v0.57/`
- Archived historical profile: retained as the repository's versioned history and not used by active defaults
- Generated codec tables: `isa/generated/codecs/`
- Sail model + coverage assets: `isa/sail/`

## Build + Validate

```bash
python3 tools/isa/build_golden.py --profile v0.56 --pretty
python3 tools/isa/validate_spec.py --profile v0.56
```

## Downstream Consumption

Compiler, emulator, and RTL integration MUST consume the compiled v0.56 catalog to avoid decode/semantic drift.

v0.57 material records the current Linx block definition for the proposed
profile. `isa/v0.57/state/downstream_migration.json` tracks the benchmark,
TileOP API, LLVM, QEMU, and GFSIM delta that must close before v0.57 becomes
the active generator default.

See also:

- `isa/generated/codecs/README.md`
