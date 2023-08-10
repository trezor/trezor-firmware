#!/usr/bin/env bash

set -e

cd $(dirname $0)

BUILDVH=$(realpath ../../tools/build_vendorheader)
BINCTL=$(realpath ../../tools/headertool.py)

for arg in "$@"; do
    if [ "$arg" == "--check" ]; then
        CHECK="--check"
    fi
    if [ "$arg" == "--quiet" ]; then
        QUIET="--quiet"
    fi
done

MODELS=(T2T1 T2B1 D001)

for MODEL in ${MODELS[@]}; do
    cd $MODEL
    # construct all vendor headers
    for fn in *.json; do
        name=$(echo $fn | sed 's/vendor_\(.*\)\.json/\1/')
        $BUILDVH $QUIET $CHECK vendor_${name}.json vendor_${name}.toif vendorheader_${name}_unsigned.bin
    done

    TMPDIR=$(mktemp -d)
    trap "rm -rf $TMPDIR" EXIT
    # sign dev and QA vendor header
    for name in unsafe qa_DO_NOT_SIGN; do
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
    cd ..
done
