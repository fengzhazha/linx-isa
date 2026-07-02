# LinxISA ISA Tooling

These tools maintain the current v0.56 stable generated catalog, codec tables,
manual fragments, and canonical-content guard.

- Latest stable profile root: `isa/v0.56/`
- Generated codecs: `isa/generated/codecs/`

## Core Commands

Build or validate the v0.56 stable generated catalog:

```bash
python3 tools/isa/build_golden.py --profile v0.56 --pretty
python3 tools/isa/build_golden.py --profile v0.56 --check
python3 tools/isa/validate_spec.py --profile v0.56
```

Generate v0.56 decode tables:

```bash
python3 tools/isa/gen_qemu_codec.py --profile v0.56 --out-dir isa/generated/codecs
python3 tools/isa/gen_c_codec.py --profile v0.56 --out-dir isa/generated/codecs
```

Generate manual fragments:

```bash
python3 tools/isa/gen_manual_adoc.py --profile v0.56 --out-dir docs/architecture/isa-manual/src/generated
python3 tools/isa/gen_instruction_fragments.py --profile v0.56 --out-dir docs/architecture/isa-manual/src/generated/instructions
python3 tools/isa/gen_ssr_adoc.py --profile v0.56 --out-dir docs/architecture/isa-manual/src/generated
```

Run the v0.56 canonical-content guard:

```bash
python3 tools/isa/check_canonical_v056.py --root .
```
