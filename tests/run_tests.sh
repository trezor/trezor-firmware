#!/bin/bash
results=()
error=0
if [ -z "$*" ]; then
    list="test_*.py"
else
    list="$*"
fi
for i in $list; do
   echo
    if ../vendor/micropython/unix/micropython $i; then
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
