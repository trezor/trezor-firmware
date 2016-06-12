#!/bin/bash

ARGS="${ARGS:--O0 -X heapsize=100000}"
MAIN="${MAIN:-main.py}"
BROWSER="${BROWSER:-chromium}"

cd `dirname $0`/src

case "$1" in
    "-d")
        shift
        gdb --args ../vendor/micropython/unix/micropython $ARGS $* $MAIN
        ;;
    "-p")
        shift
        ../vendor/micropython/unix/micropython $ARGS $* $MAIN &
        perf record -F 100 -p $! -g -- sleep 600
        perf script > perf.trace
        ../vendor/flamegraph/stackcollapse-perf.pl perf.trace | ../vendor/flamegraph/flamegraph.pl > perf.svg
        $BROWSER perf.svg
        ;;
    *)
        ../vendor/micropython/unix/micropython $ARGS $* $MAIN
esac
