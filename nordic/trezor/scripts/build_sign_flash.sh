#!/bin/bash

# Script builds, signs, and/or flashes Nordic board with optional debug or production overlays

# Run this in `nordic/trezor` to sign and mergehex final image with mcuboot
# This charade serves to differentiate commands run under uv shell and ncs shell since their pythons are not compatible

# Update the OPTSTRING to include 'a:'
OPTSTRING=":b:a:pdsfc"

APP_DIR="trezor-ble"
BOARD=
SIGN=0
FLASH=0
PRISTINE=
DEBUG=
PRODUCTION=

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
    echo "$0 [-b board_name] [-a app_dir] [-p] [-d] [-r] [-s] [-f]"
    cat <<END
    Parameters:
    -b board_name: build with board name as param
    -a app_dir: specify application directory (default: trezor-ble)
    -p: production build
    -d: use debug overlay when building
    -c: clean build (pristine)
    -s: sign result
    -f: flash board

    Each of build/sign/flash can be done in one run or separately, but the sequence must follow to make sense.
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
    c)
      PRISTINE="--pristine"
      ;;
    d)
      DEBUG="-- -DOVERLAY_CONFIG=debug.conf -Dmcuboot_EXTRA_CONF_FILE=\"$PWD/$APP_DIR/sysbuild/mcuboot.conf;$PWD/$APP_DIR/sysbuild/mcuboot_debug.conf\""
      ;;
    p)
      PRODUCTION="-- -DOVERLAY_CONFIG=prod.conf -Dmcuboot_EXTRA_CONF_FILE=\"$PWD/$APP_DIR/sysbuild/mcuboot.conf;$PWD/$APP_DIR/sysbuild/mcuboot_prod.conf\""
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
        "west build ./$APP_DIR -b $BOARD --sysbuild $PRISTINE $DEBUG $PRODUCTION"
fi

get_version_from_file() {
    local version_file="$APP_DIR/VERSION"
    if [ ! -f "$version_file" ]; then
        echo "Error: VERSION file not found at $version_file" >&2
        exit 1
    fi

    # Read version components
    local major=$(grep "VERSION_MAJOR" "$version_file" | cut -d'=' -f2 | tr -d ' ')
    local minor=$(grep "VERSION_MINOR" "$version_file" | cut -d'=' -f2 | tr -d ' ')
    local patch=$(grep "PATCHLEVEL" "$version_file" | cut -d'=' -f2 | tr -d ' ')
    local tweak=$(grep "VERSION_TWEAK" "$version_file" | cut -d'=' -f2 | tr -d ' ')

    # Format version string as major.minor.patch+tweak
    local version="$major.$minor.$patch+$tweak"

    echo "$version"
}


VERSION=$(get_version_from_file)


# Update paths in signing and flashing commands
if [ "$SIGN" -eq 1 ]; then
    run_under_ncs_subshell \
        "imgtool sign --version $VERSION --align 4 --header-size 0x200 -S 0x32000 --pad-header build/$APP_DIR/zephyr/zephyr.bin build/$APP_DIR/zephyr/zephyr.prep.bin --custom-tlv 0x00A2 0x03 --custom-tlv 0x00A3 0x54335731 && \
         imgtool sign --version $VERSION --align 4 --header-size 0x200 -S 0x32000 --pad-header build/$APP_DIR/zephyr/zephyr.hex build/$APP_DIR/zephyr/zephyr.prep.hex --custom-tlv 0x00A2 0x03 --custom-tlv 0x00A3 0x54335731  && \
         ../bootloader/mcuboot/scripts/imgtool.py dumpinfo ./build/$APP_DIR/zephyr/zephyr.prep.bin > ./build/$APP_DIR/zephyr/dump.txt"

    HASH=$(python ./scripts/extract_hash.py ./build/$APP_DIR/zephyr/dump.txt)
    SIGNATURE0=$(hash_signer -d "$HASH" -s0)
    SIGNATURE1=$(hash_signer -d "$HASH" -s1)
    echo "Signed hash $HASH, signature0 $SIGNATURE0, signature1 $SIGNATURE1"

    run_under_ncs_subshell \
        "python ./scripts/insert_signatures.py ./build/$APP_DIR/zephyr/zephyr.prep.hex $SIGNATURE0 $SIGNATURE1 -o ./build/$APP_DIR/zephyr/zephyr.signed_trz.hex && \
         python ./scripts/insert_signatures.py ./build/$APP_DIR/zephyr/zephyr.prep.bin $SIGNATURE0 $SIGNATURE1 -o ./build/$APP_DIR/zephyr/zephyr.signed_trz.bin && \
         python ../zephyr/scripts/build/mergehex.py build/mcuboot/zephyr/zephyr.hex build/$APP_DIR/zephyr/zephyr.signed_trz.hex -o build/zephyr.merged.signed_trz.hex"
fi

if [ "$FLASH" -eq 1 ]; then
    run_under_ncs_subshell \
        'west flash --hex-file ./build/zephyr.merged.signed_trz.hex'
fi
