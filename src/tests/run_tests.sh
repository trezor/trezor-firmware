#!/bin/bash
results=()
error=0
for i in test_*.py; do
   echo
    if ../../vendor/micropython/unix/micropython $i; then
       results+=("OK   $i")
    else
       results+=("FAIL $i")
       error=1
    fi
done
echo
echo 'Summary:'
printf '%s\n' "${results[@]}"
exit $error
