#!/usr/bin/env bash

function finish {
  ./record_video.sh ${CI_COMMIT_SHORT_SHA} stop
  ls -l *.mp4
}
trap finish EXIT

set -e # exit on nonzero exitcode
set -x # trace commands


./record_video.sh ${CI_COMMIT_SHORT_SHA} start
(cd ../.. && poetry install)
poetry run python bootstrap.py t1
poetry run python bootstrap.py t1 ../../trezor-*.bin
poetry run pytest ../../tests/device_tests
