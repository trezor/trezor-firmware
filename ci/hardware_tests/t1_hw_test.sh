#!/usr/bin/env bash

HERE=`dirname "$0"`
SHA=${GITHUB_SHA:-unknown}
cd $HERE

function finish {
  ./record_video.sh ${T1_CAMERA} ${SHA} stop
}
trap finish EXIT

set -e # exit on nonzero exitcode
set -x # trace commands

./record_video.sh ${T1_CAMERA} ${SHA} start
(cd ../.. && uv sync)
#uv run python bootstrap.py T1B1  # install official firmware first
uv run python bootstrap.py T1B1 ../../firmware-T1*.bin
uv run pytest ../../tests/device_tests
