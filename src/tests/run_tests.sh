#!/bin/bash
results=()
for i in *.py; do
   echo
    if ../../vendor/micropython/unix/micropython $i; then
       results+=("OK   $i")
    else
       results+=("FAIL $i")
    fi
done
echo
echo 'Summary:'
printf '%s\n' "${results[@]}"
