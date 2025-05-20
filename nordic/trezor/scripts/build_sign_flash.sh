#!/bin/bash

# Script builds, signs, and/or flashed Nordic board

# Run this in `nordic/trezor` to sign and mergehex final image with mcuboot
# This charade serves to differentiate commands run under poetry shell and ncs shell since their pythons are not compatible

OPTSTRING=":b:pdsf"

BOARD=
SIGN=0
FLASH=0
PRISTINE=
DEBUG=

fatal() {
    echo "$@"
    exit 1
}

run_under_ncs_subshell() {
    # In the subshell, toochain environment is sourced then the command is run
    # Weird regexp replaces "VARIABLE   : somevalue:bla/bla:he" to "export VARIABLE=somevalue/bla/bla/he" setting up the shell
    # Just some std::bash_ugliness::hacks
    (source <(nrfutil toolchain-manager env | perl -pe 's/^(\w+)\s*:\s*(.*)/export \1=\2/');  bash -x -c "$@") || fatal "Error in subshell"
}

usage() {
    echo "$0 [-b board_name] [-p] [-d] [-s] [-f]"
    cat<<END
    Parameters: 
    -b board_name: build with board name as param
    -p: build with --pristine
    -d: use debug overlay when building
    -s: sign result
    -f: flash board
    
    Each can build/sign/flash be done in one run or separately, but the sequence must follow to make sense"
END
}

while getopts ${OPTSTRING} opt; do
  case ${opt} in
    b)
      BOARD="$OPTARG"
      ;;
    p)
      PRISTINE="--pristine"
      ;;
    d)
      DEBUG="-- -DOVERLAY_CONFIG=debug.conf"
      ;;
    s)
      SIGN=1
      ;;
    f)
      FLASH=1
      ;;
    ?)
      usage
      exit 2
      ;;
  esac
done

if [ -n "$BOARD" ]; then
    run_under_ncs_subshell \
        "west build ./trezor-ble -b $BOARD --sysbuild $PRISTINE $DEBUG"
fi


if [ "$SIGN" -eq 1 ]; then
    run_under_ncs_subshell \
        'imgtool sign --version 0.1.0+0 --align 4 --header-size 0x200 -S 0x6c000 --pad-header build/trezor-ble/zephyr/zephyr.bin build/trezor-ble/zephyr/zephyr.prep.bin && \
         imgtool sign --version 0.1.0+0 --align 4 --header-size 0x200 -S 0x6c000 --pad-header build/trezor-ble/zephyr/zephyr.hex build/trezor-ble/zephyr/zephyr.prep.hex && \
         imgtool dumpinfo  ./build/trezor-ble/zephyr/zephyr.prep.bin > ./build/trezor-ble/zephyr/dump.txt'

    HASH=$(python ./scripts/extract_hash.py ./build/trezor-ble/zephyr/dump.txt)
    SIGNATURE=$(signer -d "$HASH" -s)
    SIGMASK=$(signer -d "$HASH" -m)
    echo "Signed hash $HASH, signature $SIGNATURE, sigmask $SIGMASK"


    run_under_ncs_subshell \
        "python ./scripts/insert_signatures_hex.py ./build/trezor-ble/zephyr/zephyr.prep.hex $SIGNATURE $SIGMASK -o ./build/trezor-ble/zephyr/zephyr.signed_cosi.hex && \
        python ./scripts/insert_signatures_bin.py ./build/trezor-ble/zephyr/zephyr.prep.bin $SIGNATURE $SIGMASK -o ./build/trezor-ble/zephyr/zephyr.signed_cosi.bin && \
        mergehex -m build/mcuboot/zephyr/zephyr.hex build/trezor-ble/zephyr/zephyr.signed_cosi.hex -o build/trezor-ble/zephyr.merged.signed.hex"
fi

if [ "$FLASH" -eq 1 ]; then
    run_under_ncs_subshell \
        'west flash --hex-file ./build/trezor-ble/zephyr.merged.signed.hex'
fi
