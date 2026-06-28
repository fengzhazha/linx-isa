#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
ZIP="${ZIP:-$HOME/Downloads/cpu2017v118_x64_gcc12_avx2.zip}"
SPEC_PARENT="${SPEC_PARENT:-$ROOT/workloads/spec2017}"
SPEC_DIR_NAME="${SPEC_DIR_NAME:-cpu2017v118_x64_gcc12_avx2}"
SPEC_DIR="$SPEC_PARENT/$SPEC_DIR_NAME"
LOG_DIR="$SPEC_DIR/tmp/linx-build-logs"
BASELINE_MANIFEST="$LOG_DIR/src-baseline.sha256"

usage() {
  cat <<EOF
Usage: reextract_cpu2017.sh [options]

Options:
  --zip <path>            SPEC2017 zip bundle path (default: $ZIP)
  --spec-parent <path>    Parent extraction directory (default: $SPEC_PARENT)
  --spec-dir-name <name>  Extracted bundle directory name (default: $SPEC_DIR_NAME)
  -h, --help              Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --zip)
      ZIP="$2"
      shift 2
      ;;
    --spec-parent)
      SPEC_PARENT="$2"
      shift 2
      ;;
    --spec-dir-name)
      SPEC_DIR_NAME="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

SPEC_PARENT="$(mkdir -p "$SPEC_PARENT" && cd "$SPEC_PARENT" && pwd -P)"
SPEC_DIR="$SPEC_PARENT/$SPEC_DIR_NAME"
LOG_DIR="$SPEC_DIR/tmp/linx-build-logs"
BASELINE_MANIFEST="$LOG_DIR/src-baseline.sha256"

if [[ ! -f "$ZIP" ]]; then
  echo "error: SPEC zip not found: $ZIP" >&2
  exit 2
fi

rm -rf "$SPEC_DIR"
unzip -q "$ZIP" -d "$SPEC_PARENT"

if [[ ! -d "$SPEC_DIR/benchspec/CPU" ]]; then
  echo "error: expected SPEC tree missing after extraction: $SPEC_DIR/benchspec/CPU" >&2
  exit 2
fi

mkdir -p "$LOG_DIR"
find "$SPEC_DIR/benchspec/CPU" -type f -path '*/src/*' -print0 \
  | LC_ALL=C sort -z \
  | xargs -0 shasum -a 256 > "$BASELINE_MANIFEST"

echo "ok: re-extracted SPEC tree: $SPEC_DIR"
echo "ok: baseline manifest: $BASELINE_MANIFEST"
