#!/usr/bin/env bash
# Downloads trezor_tests built by CI for the current build inputs (see
# inputs.sh) instead of building it. Needs gh, logged in (gh auth login).
#
# The Core workflow uploads the binary as the monero-tests-<inputs ID> artifact,
# kept for 7 days. Only artifacts from runs on the repository's own branches
# are used: a pull request from a fork can upload an artifact of any name.
#
# Usage: download.sh [OUTPUT]
# Writes OUTPUT, OUTPUT.sha256 and OUTPUT.inputs and deletes OUTPUT.chain, like
# build.sh.

set -euo pipefail

: "${TREZOR_MONERO_TESTS_REPO:=trezor/trezor-firmware}"

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [OUTPUT]" >&2
  exit 1
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
OUTPUT="${1:-$REPO/core/tests/trezor_monero_tests}"
INPUTS="$("$HERE/inputs.sh")"
NAME="monero-tests-$INPUTS"

ARTIFACT_ID="$(gh api "repos/$TREZOR_MONERO_TESTS_REPO/actions/artifacts?name=$NAME" --jq '
  [.artifacts[] | select((.expired | not) and .workflow_run.head_repository_id == .workflow_run.repository_id)]
  | first | .id // empty')"
if [[ -z "$ARTIFACT_ID" ]]; then
  echo "No $NAME artifact in $TREZOR_MONERO_TESTS_REPO: CI has not built these inputs in the last 7 days." >&2
  echo "Build the binary with core/tests/monero/build.sh instead." >&2
  exit 1
fi
echo "Downloading $NAME (artifact $ARTIFACT_ID) from $TREZOR_MONERO_TESTS_REPO"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
gh api "repos/$TREZOR_MONERO_TESTS_REPO/actions/artifacts/$ARTIFACT_ID/zip" > "$WORK/artifact.zip"
python3 -m zipfile -e "$WORK/artifact.zip" "$WORK/artifact"
(cd "$WORK/artifact" && sha256sum -c trezor_monero_tests.sha256)
if [[ "$(cat "$WORK/artifact/trezor_monero_tests.inputs")" != "$INPUTS" ]]; then
  echo "The artifact was built from other inputs than $INPUTS" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
OUT_DIR="$(cd "$(dirname "$OUTPUT")" && pwd)"
OUT_NAME="$(basename "$OUTPUT")"
cp "$WORK/artifact/trezor_monero_tests" "$OUT_DIR/$OUT_NAME"
chmod +x "$OUT_DIR/$OUT_NAME"
(cd "$OUT_DIR" && sha256sum "$OUT_NAME" > "$OUT_NAME.sha256")
echo "$INPUTS" > "$OUT_DIR/$OUT_NAME.inputs"
rm -f "$OUT_DIR/$OUT_NAME.chain"
cat "$OUT_DIR/$OUT_NAME.sha256"
