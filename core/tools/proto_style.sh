#!/usr/bin/env bash
set -euo pipefail

MODE=${1:-format}  # default to format

PROTOBUF_PATH="./common/protob"

if [[ "$MODE" == "format" ]]; then
    buf format "$PROTOBUF_PATH" -w
elif [[ "$MODE" == "check" ]]; then
    echo "buf version $(buf --version)"
    diff_output=$(buf format "$PROTOBUF_PATH" --diff)
    if [[ -n "$diff_output" ]]; then
        echo "$diff_output"
        echo
        echo "FAIL - Protobuf style-check failed."
        exit 1
    fi
    echo "OK - Protobuf style-check passed."
else
    echo "Usage: $0 [check|format]"
    exit 1
fi
