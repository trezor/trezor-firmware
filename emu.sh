#!/bin/bash
cd `dirname $0`/src
rm -f ../pipe.*
if [ "$1" == -d ]; then
    shift
    gdb --args ../vendor/micropython/unix/micropython $* -O0 -X heapsize=100000 main.py
else
    ../vendor/micropython/unix/micropython $* -O0 -X heapsize=100000 main.py
fi
rm -f ../pipe.*
