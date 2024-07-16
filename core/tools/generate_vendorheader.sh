#!/usr/bin/env bash

set -e

cd $(dirname $0)

BUILDVH=$(realpath ./build_vendorheader)
BINCTL=$(realpath ./headertool.py)

for arg in "$@"; do
    if [ "$arg" == "--check" ]; then
        CHECK="--check"
    fi
    if [ "$arg" == "--quiet" ]; then
        QUIET="--quiet"
    fi
done

cd ../embed/models/

# Find directories and store them in an array
dirs=($(find . -maxdepth 1 -type d ! -name '.' | sed 's|^\./||'))

# Filter directories that have 'vendorheader' subdirectory
MODELS=()
for dir in "${dirs[@]}"; do
    if [ -d "$dir/vendorheader" ]; then
        MODELS+=("$dir")
    fi
done

for MODEL in ${MODELS[@]}; do
    cd ./$MODEL/vendorheader
    echo "Generating vendor headers for $MODEL"
    # construct all vendor headers
    for fn in *.json; do
        $BUILDVH $QUIET $CHECK $fn
    done

    TMPDIR=$(mktemp -d)
    trap "rm -rf $TMPDIR" EXIT
    # sign dev and QA vendor header
    for name in unsafe dev_DO_NOT_SIGN; do
        SRC_NAME="vendorheader_${name}_unsigned.bin"
        DEST_NAME="vendorheader_${name}_signed_dev.bin"
        if [ ! -f "$SRC_NAME" ]; then
            continue
        fi
        cp -a vendorheader_${name}_unsigned.bin "$TMPDIR/$DEST_NAME"
        $BINCTL $QUIET -D "$TMPDIR/$DEST_NAME"
        if [ -n "$CHECK" ]; then
            diff "$DEST_NAME" "$TMPDIR/$DEST_NAME"
        fi
        cp -a "$TMPDIR/$DEST_NAME" "$DEST_NAME"
    done
    cd ../../
done
