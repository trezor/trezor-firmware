#!/bin/bash

cd $(dirname $0)
MICROPYTHON=../build/unix/micropython
PYOPT=1

results=()
error=0

if [ -z "$*" ]; then
    list="test_*.py"
else
    list="$*"
fi

for i in $list; do
    echo
    if $MICROPYTHON -O$PYOPT $i; then
        results+=("OK   $i")
    else
        results+=("FAIL $i")
        error=1
    fi
done

echo
echo 'Summary:'
printf '%s\n' "${results[@]}"
echo '-------------------'
if [ $error == 0 ]; then
    echo 'ALL OK'
else
    echo 'FAIL at least one error occurred'
fi
exit $error
