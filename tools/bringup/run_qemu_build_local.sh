#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
QEMU_ROOT="${QEMU_ROOT:-$ROOT/emulator/qemu}"
OUT_DIR="${OUT_DIR:-/private/tmp/linx-qemu-local-build}"
TARGET="${TARGET:-qemu-system-linx64}"
NINJA_BIN="${NINJA_BIN:-}"

usage() {
  cat <<'USAGE'
Usage: tools/bringup/run_qemu_build_local.sh [options]

Options:
  --qemu-root PATH     QEMU source tree (default: $ROOT/emulator/qemu)
  --out-dir PATH       Local build directory (default: /private/tmp/linx-qemu-local-build)
  --target NAME        Build target (default: qemu-system-linx64)
  --ninja PATH         Ninja executable

Behavior:
  Configures and incrementally rebuilds the current local QEMU source tree.
  This is the preferred bring-up path when validating the live dirty-source
  Linx QEMU line rather than the detached clean-worktree lane.

Stdout:
  Prints the absolute path to the requested built target on success.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --qemu-root)
      QEMU_ROOT="$2"
      shift 2
      ;;
    --out-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    --target)
      TARGET="$2"
      shift 2
      ;;
    --ninja)
      NINJA_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -d "$QEMU_ROOT" ]]; then
  echo "error: qemu root does not exist: $QEMU_ROOT" >&2
  exit 2
fi

if [[ -z "$NINJA_BIN" ]]; then
  for cand in "/opt/homebrew/bin/ninja" "$(command -v ninja 2>/dev/null || true)"; do
    if [[ -n "$cand" && -x "$cand" ]]; then
      NINJA_BIN="$cand"
      break
    fi
  done
fi

if [[ -z "$NINJA_BIN" || ! -x "$NINJA_BIN" ]]; then
  echo "error: ninja not found; set --ninja or NINJA_BIN" >&2
  exit 2
fi

mkdir -p "$OUT_DIR"
TARGET_PATH="$OUT_DIR/$TARGET"
LOCK_DIR="$OUT_DIR/.linx_qemu_local_build.lock"

cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

while ! mkdir "$LOCK_DIR" 2>/dev/null; do
  echo "info: waiting for local qemu build lock: $LOCK_DIR" >&2
  sleep 1
done
trap cleanup EXIT INT TERM

if [[ ! -f "$OUT_DIR/build.ninja" ]]; then
  echo "info: configuring local qemu build in $OUT_DIR" >&2
  (
    cd "$OUT_DIR"
    LINX_MODEL_INCLUDE="$ROOT/tools/model/include" \
      "$QEMU_ROOT/configure" \
      --target-list=linx64-softmmu \
      --enable-plugins \
      --disable-docs \
      --disable-werror \
      --disable-install-blobs >&2
  )
fi

echo "info: building $TARGET in $OUT_DIR" >&2
"$NINJA_BIN" -C "$OUT_DIR" "$TARGET" >&2

if [[ ! -x "$TARGET_PATH" ]]; then
  echo "error: built target not found: $TARGET_PATH" >&2
  exit 1
fi

printf '%s\n' "$TARGET_PATH"
