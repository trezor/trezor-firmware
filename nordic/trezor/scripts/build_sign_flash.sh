#!/bin/bash

# Script builds, signs, and/or flashes Nordic board with optional debug or production overlays

# Run this in `nordic/trezor` to sign and mergehex final image with mcuboot
# This charade serves to differentiate commands run under uv shell and ncs shell since their pythons are not compatible

# Update the OPTSTRING to include 'a:'
OPTSTRING=":b:a:pdfc"

APP_DIR="trezor-ble"
BOARD=
FLASH=0
PRISTINE=
DEBUG=0
PRODUCTION=${PRODUCTION:-0}
OVERLAY_CONFIG=

fatal() {
    echo "$@"
    exit 1
}

# Auto-detect environment and choose appropriate execution method
detect_environment() {
    # Check if we're in Docker environment for reproducible build
    # e.g. Docker/Nix with pre-configured toolchain for reproducible build
    if [ -n "$GNUARMEMB_TOOLCHAIN_PATH" ] && [ -n "$ZEPHYR_TOOLCHAIN_VARIANT" ]; then
        return 0  # Use direct execution
    elif command -v nrfutil > /dev/null 2>&1; then
        # We have nrfutil available (local development)
        return 1  # Use nrfutil subshell
    else
        # Fallback to direct execution
        echo "Warning: Neither nrfutil nor pre-configured toolchain detected, using direct execution"
        return 0
    fi
}

run_under_ncs_subshell() {
    detect_environment
    local use_direct=$?

    if [ $use_direct -eq 0 ]; then
        # Docker/Nix environment - run directly
        eval "$@" || fatal "Error in direct command execution"
    else
        # Local development environment - use nrfutil
        (source <(nrfutil toolchain-manager env | perl -pe 's/^(\w+)\s*:\s*(.*)/export \1=\2/'); bash -x -c "$@") \
            || fatal "Error in nrfutil subshell"
    fi
}

usage() {
    echo "$0 [-b board_name] [-a app_dir] [-p] [-d] [-c] [-f]"
    cat <<END
    Parameters:
    -b board_name: build with board name as param, and sign with dev keys
    -a app_dir: specify application directory (default: trezor-ble)
    -p: production build
    -d: use debug overlay when building
    -c: clean build (pristine)
    -f: flash board

    Each of build/flash can be done in one run or separately, but the sequence must follow to make sense.
END
}

while getopts ${OPTSTRING} opt; do
  case ${opt} in
    b)
      BOARD="$OPTARG"
      ;;
    a)
      APP_DIR="$OPTARG"
      ;;
    m)
      TREZOR_MODEL="$OPTARG"
      ;;
    c)
      PRISTINE="--pristine"
      ;;
    d)
      DEBUG=1
      ;;
    p)
      PRODUCTION=1
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

if [ "$DEBUG" -eq 1 ]; then
  if [ "$PRODUCTION" -eq 1 ]; then
    fatal "Cannot build both debug and production at the same time"
  fi
  PRODUCTION=0
fi

if [ "$DEBUG" -eq 1 ]; then
  OVERLAY_CONFIG="-- -DOVERLAY_CONFIG=debug.conf -Dmcuboot_EXTRA_CONF_FILE=\"$PWD/$APP_DIR/sysbuild/mcuboot.conf;$PWD/$APP_DIR/sysbuild/mcuboot_debug.conf\""
elif [ "$PRODUCTION" -eq 1 ]; then
  OVERLAY_CONFIG="-- -DOVERLAY_CONFIG=prod.conf -Dmcuboot_EXTRA_CONF_FILE=\"$PWD/$APP_DIR/sysbuild/mcuboot.conf;$PWD/$APP_DIR/sysbuild/mcuboot_prod.conf\""
fi

if [ -n "$BOARD" ]; then
    run_under_ncs_subshell \
        "west build ./$APP_DIR -b $BOARD --sysbuild $PRISTINE $OVERLAY_CONFIG"

  # Update paths in signing and flashing commands
  nrftool wrap build/$APP_DIR/zephyr/zephyr.bin -o build/$APP_DIR/zephyr/zephyr.wrapped.bin -b $BOARD
  nrftool sign-dev build/$APP_DIR/zephyr/zephyr.wrapped.bin
  nrftool wrap build/$APP_DIR/zephyr/zephyr.hex -o build/$APP_DIR/zephyr/zephyr.wrapped.hex -b $BOARD
  nrftool sign-dev build/$APP_DIR/zephyr/zephyr.wrapped.hex
  python ../zephyr/scripts/build/mergehex.py build/mcuboot/zephyr/zephyr.hex build/$APP_DIR/zephyr/zephyr.wrapped.hex -o build/zephyr.merged.signed_trz.hex
fi

if [ "$FLASH" -eq 1 ]; then
    run_under_ncs_subshell \
        'west flash --hex-file ./build/zephyr.merged.signed_trz.hex'
fi
