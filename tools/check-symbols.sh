#!/usr/bin/env bash

set -eu

trap 'echo "🔴 FAILED"' EXIT

if [ $# -eq 0 ]; then
    echo "No ELF files specified"
    exit 1
fi

for ELF in $@
do
    echo "🔵 $ELF"
    arm-none-eabi-nm --line-numbers "$ELF" > "$ELF.symbols"
    grep -E 'insecure|random_reseed|debug' "$ELF.symbols" --color && exit 1
done

trap 'echo "🟢 OK"' EXIT
