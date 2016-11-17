#!/bin/bash

source emu.config 2>/dev/null

OPTLEVEL="${OPTLEVEL:-0}"
HEAPSIZE="${HEAPSIZE:-100000}"
MAIN="${MAIN:-main.py}"
BROWSER="${BROWSER:-chromium}"

ARGS="-O${OPTLEVEL} -X heapsize=${HEAPSIZE}"

cd `dirname $0`/src

case "$1" in
    "-d")
        shift
        gdb --args ../vendor/micropython/unix/micropython $ARGS $* $MAIN
        ;;
    "-r")
        shift
        while true; do
            ../vendor/micropython/unix/micropython $ARGS $* $MAIN &
            UPY_PID=$!
            find -name '*.py' | inotifywait -q -e close_write --fromfile -
            echo Restarting ...
            kill $UPY_PID
        done
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
