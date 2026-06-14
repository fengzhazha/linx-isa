# LinxISA Repo Audit - 2026-06-14

## Scope

This note captures the current repository map and the validation evidence
gathered while closing the Linux/QEMU and TSVC compiler bring-up lanes.

It is not a generated status dashboard. It is a human-readable audit snapshot
backed by concrete commands and current in-repo paths.

## Canonical repo map

- Superproject navigation contract: `docs/project/navigation.md`
- ISA source of truth: `isa/v0.56/linxisa-v0.56.json`
- Public architecture contract: `docs/architecture/v0.56-architecture-contract.md`
- Runtime AVS root: `avs/qemu/`
- Compiler AVS root: `avs/compiler/linx-llvm/tests/`
- Freestanding runtime support used by AVS/tests: `avs/runtime/freestanding/`
- LLVM target backend: `compiler/llvm/llvm/lib/Target/LinxISA/`
- QEMU target: `emulator/qemu/target/linx/`
- Linux arch port: `kernel/linux/arch/linx/`
- Published LinxCore architecture mirror: `docs/architecture/linxcore/`
- Canonical LinxCore architecture source: `rtl/LinxCore/docs/architecture/`
- Assembly examples: `docs/reference/examples/v0.56/`
- TSVC workload flow: `workloads/tsvc/`

## Verified gates

### ISA and architecture

Commands run:

- `python3 tools/isa/build_golden.py --profile v0.56 --check`
- `python3 tools/isa/validate_spec.py --profile v0.56`
- `python3 tools/isa/check_canonical_v056.py --root /Users/zhoubot/linx-isa`
- `python3 tools/bringup/check_linxcore_arch_contract.py --root /Users/zhoubot/linx-isa --strict`
- `python3 tools/bringup/check_linxcore_arch_contract.py --root /Users/zhoubot/linx-isa --strict --require-mkdocs`

Result:

- All five commands pass on the current worktree.
- LinxCore architecture docs are now synchronized to the enforced `v0.56`
  contract across canonical source and published mirror.

### Compiler AVS and assembly surfaces

Commands run:

- `cd avs/compiler/linx-llvm/tests && CLANG=/Users/zhoubot/linx-isa/compiler/llvm/build-linxisa-clang/bin/clang TARGET=linx64-linx-none-elf OUT_DIR=/Users/zhoubot/linx-isa/avs/compiler/linx-llvm/tests/out-linx64 ./run.sh`
- `python3 avs/compiler/linx-llvm/tests/analyze_coverage.py --out-dir /Users/zhoubot/linx-isa/avs/compiler/linx-llvm/tests/out-linx64 --fail-under 100`
- `cd avs/compiler/linx-llvm/tests && CLANG=/Users/zhoubot/linx-isa/compiler/llvm/build-linxisa-clang/bin/clang TARGET=linx32-linx-none-elf OUT_DIR=/Users/zhoubot/linx-isa/avs/compiler/linx-llvm/tests/out-linx32 ./run.sh`
- `python3 avs/compiler/linx-llvm/tests/analyze_coverage.py --out-dir /Users/zhoubot/linx-isa/avs/compiler/linx-llvm/tests/out-linx32 --fail-under 100`

Result:

- `linx64` AVS compile suite passes.
- `linx32` AVS compile suite passes.
- Both coverage analyzers report `710/710` unique v0.56 mnemonics covered.
- The active assembly-surface proof includes:
  - `41_v056_isa_forms`
  - `99_spec_decode`
  - call/ret template checks `33` through `38`
  - negative rejection probes for legacy `L.BSTOP` and TEPL tileop range

### Linux on QEMU

Command run:

- `python3 avs/qemu/run_linux_boot_proofs.py`

Result:

- Userspace boot proof passes.
- Poweroff proof passes.
- The Linux/QEMU lane is currently green on the in-repo runtime path.

### QEMU runtime AVS breadth

Commands run:

- `python3 avs/qemu/run_callret_contract.py --qemu /private/tmp/linx-qemu-local-build/qemu-system-linx64`
- `python3 avs/qemu/run_tests.py --suite loadstore --qemu /private/tmp/linx-qemu-local-build/qemu-system-linx64 --verbose`
- `python3 tools/bringup/check_qemu_opcode_meta_sync.py --qemu-root emulator/qemu ...`
- `python3 tools/bringup/report_qemu_isa_coverage.py --spec isa/v0.56/linxisa-v0.56.json --qemu-meta emulator/qemu/target/linx/linx_opcode_meta_gen.h ...`

Result:

- Call/ret contract trap validation passes.
- `loadstore` suite passes after fixing the prefetch inline-asm surface and
  the runner/finisher interpretation path.
- QEMU ISA coverage currently reports `615/710` mapped spec mnemonics and
  `614/740` mapped spec forms.
- The opcode-sync audit now understands the modern `insn*.decode` layout, but
  still reports one unexpected decode-only drift: `bstart_fall`.

Current blocker:

- The broader `system` runtime suite is not closed.
- Current local QEMU evidence shows `TESTID_PRIV_FLOW` (`0x1102`) reaches the
  IRQ return path and then spins at PC `0x10af0` (the `acrc` in
  `linx_priv_after_irq`) with `cstate=0x0`, rather than completing the
  privilege-flow sequence.

### TSVC compiler maturity lane

Commands run:

- `python3 workloads/tsvc/run_tsvc.py ... --kernel-regex '^(s332)$'`
- `python3 workloads/tsvc/run_tsvc.py ... --kernel-regex '^(s4117)$'`
- `python3 workloads/tsvc/run_tsvc.py ... --kernel-regex '^(s452)$'`
- `python3 workloads/tsvc/run_tsvc_batched.py --batch-size 20 ... --strict-fail-under 151 --out-dir /Users/zhoubot/linx-isa/workloads/generated-tsvc-strict-batched20-cleanqemu-v6`

Result:

- `s332`, `s4117`, and `s452` all lower successfully on the current compiler.
- Batched strict TSVC coverage is `151/151`.
- The reproducible aggregate artifact root is:
  `workloads/generated-tsvc-strict-batched20-cleanqemu-v6`

## Key implementation findings

- The compiler needed a grouped-lane `v.icvtf` path plus blockify/MC pseudo
  support to avoid scalar-replay regressions in `s452`.
- Shifted-address grouped layouts such as `c[i/2]` now stay on the grouped
  lane instead of falling back unnecessarily.
- Search-style TSVC loops such as `s332` were blocked by an over-strict
  exit-chain filter that rejected pure values feeding exit PHIs. Relaxing that
  filter restored legal `MSEQ` lowering.
- The TSVC strict lane is more reproducible through
  `workloads/tsvc/run_tsvc_batched.py`, with the proven default batch size set
  to `20`.

## Current local closure state

- `compiler/llvm` contains the validated TSVC closure commits.
- `rtl/LinxCore` contains the validated architecture-doc sync commit.
- The superproject should repin both submodules after review so `main`
  references the validated SHAs.

## Remaining broader work

- This audit does not claim full cross-repo bring-up closure beyond the gates
  listed above.
- It does not yet rerun the full `tools/regression/strict_cross_repo.sh`
  matrix.
- It does not yet summarize every non-compiler subsystem under `rtl/`,
  `tools/pyCircuit/`, `lib/`, and `kernel/` beyond the validated surfaces
  above.
