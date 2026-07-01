# LinxISA ISA Tooling

These tools include the latest v0.57 PTO/block validation gates and the
previous v0.56 generated-catalog utilities.

- Latest profile root: `isa/v0.57/`
- Latest block/PTO encoding checks: `tools/isa/check_pto_v057_*.py`
- Previous generated catalog root: `isa/v0.56/`
- Previous generated codecs: `isa/generated/codecs/`

## Core Commands

Validate the latest v0.57 PTO block encoding:

```bash
python3 tools/isa/check_pto_v057_encoding.py --spec isa/v0.57/state/pto_encoding.json
```

Audit latest v0.57 downstream synchronization:

```bash
python3 tools/isa/check_pto_v057_downstream.py
python3 tools/isa/check_pto_v057_downstream.py --strict
```

Build or validate the previous v0.56 generated catalog when maintaining the
existing scalar codec generator:

```bash
python3 tools/isa/build_golden.py --profile v0.56 --pretty
python3 tools/isa/validate_spec.py --profile v0.56
```

Generate previous v0.56 decode tables:

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

Run the previous v0.56 canonical-content guard:

```bash
python3 tools/isa/check_canonical_v056.py --root .
```
