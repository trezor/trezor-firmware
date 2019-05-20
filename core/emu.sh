#!/bin/bash

MICROPYTHON="${MICROPYTHON:-${PWD}/build/unix/micropython}"
TREZOR_SRC=$(cd "${PWD}/src/"; pwd)
BROWSER="${BROWSER:-chromium}"

source ./trezor_cmd.sh

cd "${TREZOR_SRC}"

case "$1" in
    "-d")
        shift
        OPERATING_SYSTEM=$(uname)
        if [ $OPERATING_SYSTEM == "Darwin" ]; then
            PATH=/usr/bin /usr/bin/lldb -f $MICROPYTHON -- $ARGS $* $MAIN
        else
            gdb --args $MICROPYTHON $ARGS $* $MAIN
        fi
        ;;
    "-r")
        shift
        while true; do
            $MICROPYTHON $ARGS $* $MAIN &
            UPY_PID=$!
            find -name '*.py' | inotifywait -q -e close_write --fromfile -
            echo Restarting ...
            kill $UPY_PID
        done
        ;;
    *)
        echo "Starting emulator: $MICROPYTHON $ARGS $* $MAIN"
        $MICROPYTHON $ARGS $* $MAIN 2>&1 | tee "${TREZOR_LOGFILE}"
        exit ${PIPESTATUS[0]}
esac
