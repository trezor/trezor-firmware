#!/usr/bin/env bash

cd $(dirname $0)

BUILDVH=$(realpath ../../tools/build_vendorheader)
BINCTL=$(realpath ../../tools/headertool.py)

MODELS=(T2T1 T2B1 D001)

for MODEL in ${MODELS[@]}; do
    cd $MODEL
    # construct all vendor headers
    for fn in *.json; do
        name=$(echo $fn | sed 's/vendor_\(.*\)\.json/\1/')
        $BUILDVH vendor_${name}.json vendor_${name}.toif vendorheader_${name}_unsigned.bin
    done

    # sign dev and QA vendor header
    for name in unsafe qa_DO_NOT_SIGN; do
        cp -a vendorheader_${name}_unsigned.bin vendorheader_${name}_signed_dev.bin
        $BINCTL -D vendorheader_${name}_signed_dev.bin
    done
    cd ..
done
