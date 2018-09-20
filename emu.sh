#!/bin/bash

source emu.config 2>/dev/null

EXE=build/unix/micropython
PYOPT="${PYOPT:-1}"
MAIN="${MAIN:-main.py}"
BROWSER="${BROWSER:-chromium}"
HEAPSIZE="${HEAPSIZE:-800K}"
SOURCE_PY_DIR="${SOURCE_PY_DIR:-src}"

ARGS="-O${PYOPT} -X heapsize=${HEAPSIZE}"

cd `dirname $0`/$SOURCE_PY_DIR

case "$1" in
    "-d")
        shift
        gdb --args ../$EXE $ARGS $* $MAIN
        ;;
    "-r")
        shift
        while true; do
            ../$EXE $ARGS $* $MAIN &
            UPY_PID=$!
            find -name '*.py' | inotifywait -q -e close_write --fromfile -
            echo Restarting ...
            kill $UPY_PID
        done
        ;;
    "-p")
        shift
        ../$EXE $ARGS $* $MAIN &
        perf record -F 100 -p $! -g -- sleep 600
        perf script > perf.trace
        ../vendor/flamegraph/stackcollapse-perf.pl perf.trace | ../vendor/flamegraph/flamegraph.pl > perf.svg
        $BROWSER perf.svg
        ;;
    *)
        ../$EXE $ARGS $* $MAIN
esac
