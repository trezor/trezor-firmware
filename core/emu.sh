#!/bin/sh

if [ -f emu.config ]; then
    . emu.config
fi

EXE=build/unix/micropython
PYOPT="${PYOPT:-1}"
MAIN="${MAIN:-src/main.py}"
HEAPSIZE="${HEAPSIZE:-50M}"

ARGS="-O${PYOPT} -X heapsize=${HEAPSIZE}"

cd `dirname $0`

case "$1" in
    "-d")
        shift
        OPERATING_SYSTEM=$(uname)
        if [ "$OPERATING_SYSTEM" = "Darwin" ]; then
            PATH=/usr/bin /usr/bin/lldb -f $EXE -- $ARGS $* $MAIN
        else
            gdb --args $EXE $ARGS $* $MAIN
        fi
        ;;
    "-r")
        shift
        while true; do
            $EXE $ARGS $* $MAIN &
            UPY_PID=$!
            find -name '*.py' | inotifywait -q -e close_write --fromfile -
            echo Restarting ...
            kill $UPY_PID
        done
        ;;
    *)
        $EXE $ARGS $* $MAIN
esac
