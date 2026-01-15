#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/trezor-api-bindings.XXXXXX")"

if [[ "${KEEP_TMP:-0}" == "1" ]]; then
    echo "KEEP_TMP=1, preserving: $TMP_DIR"
else
    trap 'rm -rf "$TMP_DIR"' EXIT
fi

build_and_extract() {
    local name="$1"
    local model="$2"
    local target="$3"
    local out="$TMP_DIR/${name}.rs"

    rm -f "$out"

    echo "==> TREZOR_MODEL=${model} make ${target}"
    (
        cd "$ROOT_DIR"
        TREZOR_API_RS_OUT="$out" QUIET_MODE=1 TREZOR_MODEL="$model" make -C core "$target"
    )

    if [[ ! -f "$out" ]]; then
        echo "ERROR: missing output $out (generate_api_bindings did not export it)" >&2
        exit 1
    fi
    if [[ ! -s "$out" ]]; then
        echo "ERROR: empty output $out" >&2
        exit 1
    fi

    echo "    written: $out"
}

compare() {
    local lhs="$1"
    local rhs="$2"
    local l="$TMP_DIR/${lhs}.rs"
    local r="$TMP_DIR/${rhs}.rs"

    [[ -f "$l" ]] || { echo "ERROR: missing $l" >&2; exit 1; }
    [[ -f "$r" ]] || { echo "ERROR: missing $r" >&2; exit 1; }

    if ! cmp -s "$l" "$r"; then
        echo "FAIL: api.rs mismatch between '${lhs}' and '${rhs}'" >&2
        diff -u "$l" "$r" || true
        exit 1
    fi
    echo "OK: ${lhs} == ${rhs}"
}

build_and_extract "t3w1_fw"  "T3W1" "build_firmware"
build_and_extract "t3w1_emu" "T3W1" "build_unix"
build_and_extract "t3t1_fw"  "T3T1" "build_firmware"
build_and_extract "t3t1_emu" "T3T1" "build_unix"

compare t3w1_fw t3w1_emu
compare t3w1_fw t3t1_fw
compare t3w1_fw t3t1_emu

echo "All 4 generated api.rs files are identical."

# copy canonical generated bindings to app sdk ffi.rs
DEST_FFI="${ROOT_DIR}/sdk/crates/trezor-app-sdk/src/low_level_api/ffi.rs"
cp "${TMP_DIR}/t3w1_fw.rs" "${DEST_FFI}"
echo "Updated: ${DEST_FFI}"
