#!/bin/sh

CURR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
CORE_DIR=$(realpath "${CURR_DIR}/../..")

export BINSIZE_ROOT_DIR="${CORE_DIR}"
binsize build $@
