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
HEADER_SIZE=
SLOT_ADDR=
SLOT_SIZE=
MODEL_IDENTIFIER=
# Resolved by verify_environment(); pins the toolchain used by the build subshell.
NCS_TOOLCHAIN_VERSION=

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
        # Local development environment - use nrfutil. Pin the toolchain to the
        # version resolved by verify_environment() so the build does not silently
        # use whatever toolchain happens to be the active ('*') default.
        local tcm_env="nrfutil toolchain-manager env"
        [ -n "$NCS_TOOLCHAIN_VERSION" ] && tcm_env="$tcm_env --ncs-version $NCS_TOOLCHAIN_VERSION"
        (source <($tcm_env | perl -pe 's/^(\w+)\s*:\s*(.*)/export \1=\2/'); bash -x -c "$@") \
            || fatal "Error in nrfutil subshell"
    fi
}

# Run host-side signing/merge tools in the *current* shell. imgtool, hash_signer
# and the helper Python scripts come from the uv/.venv (or nix) environment and
# must NOT inherit the NCS toolchain's Python env (PYTHONHOME), which points a
# different-version interpreter at the wrong stdlib ("SRE module mismatch").
# Only 'west build'/'west flash' need the NCS toolchain (run_under_ncs_subshell).
run_native() {
    eval "$@" || fatal "Error running host command: $*"
}

usage() {
    echo "$0 [-b board_name] [-a app_dir] [-p] [-d] [-r] [-s] [-f]"
    cat <<END
    Parameters:
    -b board: full board target (e.g. t3t2_dk/nrf54ls05b/cpuapp) or a model
              alias (t3t2, t3w1) that expands to that model's default board
    -a app_dir: specify application directory (default: trezor-ble)
    -p: production build
    -d: use debug overlay when building
    -c: clean build (pristine)
    -s: sign result
    -f: flash board

    Each of build/sign/flash can be done in one run or separately, but the sequence must follow to make sense.
END
}

parse_partition_info() {
    local dts_file="build/$APP_DIR/zephyr/zephyr.dts"
    local config_file="build/$APP_DIR/zephyr/.config"

    [ -f "$dts_file" ]    || fatal "DTS not found: $dts_file (run a build first)"
    [ -f "$config_file" ] || fatal "Kconfig not found: $config_file (run a build first)"

    local reg_line
    reg_line=$(awk '/slot0_partition:/{f=1} f && /reg[[:space:]]*=/{print; f=0}' "$dts_file")
    [ -n "$reg_line" ] || fatal "slot0_partition node not found in $dts_file"

    SLOT_ADDR=$(echo "$reg_line" | grep -oE '0x[0-9a-fA-F]+' | sed -n '1p')
    SLOT_SIZE=$(echo "$reg_line" | grep -oE '0x[0-9a-fA-F]+' | sed -n '2p')
    [ -n "$SLOT_ADDR" ] || fatal "Could not parse slot address from slot0_partition in $dts_file"
    [ -n "$SLOT_SIZE" ] || fatal "Could not parse slot size from slot0_partition in $dts_file"

    HEADER_SIZE=$(grep "^CONFIG_ROM_START_OFFSET=" "$config_file" | cut -d'=' -f2)
    [ -n "$HEADER_SIZE" ] || fatal "CONFIG_ROM_START_OFFSET not found in $config_file"

    # CONFIG_MODEL_IDENTIFIER stores the 4-char ASCII tag as a little-endian uint32
    # (e.g. "T3W1" → 0x31573354). imgtool --custom-tlv needs the big-endian form,
    # so byte-swap the 8 hex digits.
    local model_id_dec
    model_id_dec=$(grep "^CONFIG_MODEL_IDENTIFIER=" "$config_file" | cut -d'=' -f2)
    [ -n "$model_id_dec" ] || fatal "CONFIG_MODEL_IDENTIFIER not found in $config_file"
    local hex
    hex=$(printf '%08x' "$model_id_dec")
    MODEL_IDENTIFIER="0x${hex:6:2}${hex:4:2}${hex:2:2}${hex:0:2}"
}

# Verify the active nRF Connect SDK / toolchain match the target board before
# building. Each board is pinned to one SDK: t3w1 -> NCS 2.9 (west-ncs2.9.yml),
# t3t2_dk/nRF54L -> NCS 3.3 (west.yml, default). Building with the wrong SDK or
# toolchain active produces confusing, hard-to-diagnose failures.
verify_environment() {
    local board="$1"
    local required_major expected_manifest
    case "$board" in
        t3w1*)   required_major=2; expected_manifest="west-ncs2.9.yml" ;;
        t3t2_dk*) required_major=3; expected_manifest="west.yml" ;;
        *)
            echo "verify: board '$board' has no known SDK pairing; skipping SDK/toolchain check."
            return 0
            ;;
    esac

    # Authoritative: the SDK actually checked out into the workspace by the last
    # 'west update'. This is what the build will really use, regardless of what
    # 'west config manifest.file' currently says.
    local nrf_version_file="../nrf/VERSION"
    [ -f "$nrf_version_file" ] || fatal "verify: cannot read $nrf_version_file - is the west workspace initialized and updated?"
    local sdk_version sdk_major sdk_mm
    sdk_version=$(tr -d '[:space:]' < "$nrf_version_file")
    sdk_major="${sdk_version%%.*}"
    sdk_mm="${sdk_version%.*}"   # major.minor, e.g. 2.9

    if [ "$sdk_major" != "$required_major" ]; then
        fatal "verify: board '$board' requires NCS v${required_major}.x, but the checked-out SDK is v${sdk_version}.
Select the matching manifest, update the workspace, then rebuild pristine:
    (cd .. && west config manifest.file ${expected_manifest} && west update)
    $0 -b ${board} <flags> -c"
    fi

    # West manifest selection (advisory; the SDK check above is authoritative).
    if command -v west >/dev/null 2>&1; then
        local active_manifest
        active_manifest=$(west config manifest.file 2>/dev/null)
        if [ -n "$active_manifest" ] && [ "$active_manifest" != "$expected_manifest" ]; then
            echo "verify: WARNING active west manifest is '$active_manifest' (expected '$expected_manifest' for '$board')."
            echo "        Checked-out SDK v${sdk_version} matches the board; run 'west update' if you just changed the manifest."
        fi
    fi

    # Toolchain selection depends on the execution environment (see
    # detect_environment): under nix/Docker the toolchain is pre-provided via
    # GNUARMEMB_TOOLCHAIN_PATH and the build runs directly, so there is nothing
    # to pin. Only the local nrfutil path needs a pinned toolchain.
    if [ -n "$GNUARMEMB_TOOLCHAIN_PATH" ] && [ -n "$ZEPHYR_TOOLCHAIN_VARIANT" ]; then
        echo "verify: OK - board '$board' <-> NCS v${sdk_version} (manifest ${expected_manifest}); using pre-set ${ZEPHYR_TOOLCHAIN_VARIANT} toolchain."
        return 0
    fi

    # Local nrfutil path: 'nrfutil toolchain-manager list' marks the active/default
    # toolchain with a leading '*'. The build subshell sources 'toolchain-manager
    # env', which returns that active toolchain unless we pin one - so resolve the
    # toolchain matching the checked-out SDK and pin the build to it.
    if command -v nrfutil >/dev/null 2>&1; then
        local tc_list active_tc resolved_tc
        tc_list=$(nrfutil toolchain-manager list 2>/dev/null)
        active_tc=$(echo "$tc_list" | awk '$1=="*"{print $2}')
        # Prefer an exact match for the checked-out SDK, else any vMAJOR.MINOR.*.
        resolved_tc=$(echo "$tc_list" | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | grep -xE "v${sdk_version}" | head -1)
        [ -n "$resolved_tc" ] || resolved_tc=$(echo "$tc_list" | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | grep -E "^v${sdk_mm}\." | head -1)

        if [ -z "$resolved_tc" ]; then
            fatal "verify: no NCS v${sdk_mm}.x toolchain installed (needed for '$board').
Install it with:
    nrfutil toolchain-manager install --ncs-version v${sdk_mm}.0"
        fi

        NCS_TOOLCHAIN_VERSION="$resolved_tc"
        if [ "$active_tc" != "$resolved_tc" ]; then
            echo "verify: active toolchain is '${active_tc:-none}', but '$board' needs NCS v${sdk_mm}.x;"
            echo "        pinning this build to toolchain ${resolved_tc}."
        fi
    fi

    echo "verify: OK - board '$board' <-> NCS v${sdk_version}, toolchain ${NCS_TOOLCHAIN_VERSION:-<pre-set>} (manifest ${expected_manifest})."
}

# Resolve a friendly board alias to its canonical Zephyr board target. Lets you
# pass just a model name (e.g. "t3t2") and get that model's default board, while
# a full board target (anything containing '/', e.g. "t3t2_dk/nrf54ls05b/cpuapp")
# or any unrecognised value passes through unchanged - so a specific board can
# always be selected explicitly.
resolve_board() {
    case "$1" in
        t3t2)  echo "t3t2_dk/nrf54ls05b/cpuapp" ;;
        t3w1)  echo "t3w1_revA_nrf52832" ;;
        *)     echo "$1" ;;
    esac
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
      # Force a full wipe (not 'auto'): switching SDK/toolchain leaves a
      # CMakeCache.txt with stale toolchain paths (ninja, zephyr-sdk) that 'auto'
      # will not detect because the board is unchanged.
      PRISTINE="--pristine=always"
      ;;
    d)
      DEBUG="-DOVERLAY_CONFIG=debug.conf -Dmcuboot_EXTRA_CONF_FILE=\"$PWD/$APP_DIR/sysbuild/mcuboot.conf;$PWD/$APP_DIR/sysbuild/mcuboot_debug.conf\""
      ;;
    p)
      PRODUCTION="-DOVERLAY_CONFIG=prod.conf -Dmcuboot_EXTRA_CONF_FILE=\"$PWD/$APP_DIR/sysbuild/mcuboot.conf;$PWD/$APP_DIR/sysbuild/mcuboot_prod.conf\""
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
    resolved_board=$(resolve_board "$BOARD")
    if [ "$resolved_board" != "$BOARD" ]; then
        echo "board: alias '$BOARD' -> '$resolved_board'"
        BOARD="$resolved_board"
    fi
    verify_environment "$BOARD"

    # Board-scoped sysbuild overlays. The ed25519 image-hash override symbol
    # (SB_CONFIG_BOOT_IMG_HASH_ALG_SHA512) only exists on nRF54L / NCS 3.3, so
    # it must not live in the shared sysbuild.conf - assigning it on nRF52832 /
    # NCS 2.9 aborts the build with an "undefined symbol" Kconfig warning.
    SB_OVERLAY=
    case "$BOARD" in
        t3t2_dk*) SB_OVERLAY="-DSB_EXTRA_CONF_FILE=$PWD/$APP_DIR/sysbuild_nrf54l.conf" ;;
    esac

    # Assemble all post-'--' cmake args; emit the '--' separator only if any exist.
    EXTRA_CMAKE_ARGS="$DEBUG $PRODUCTION $SB_OVERLAY"
    CMAKE_SEP=
    [ -n "${EXTRA_CMAKE_ARGS// /}" ] && CMAKE_SEP="--"

    run_under_ncs_subshell \
        "west build ./$APP_DIR -b $BOARD --sysbuild $PRISTINE $CMAKE_SEP $EXTRA_CMAKE_ARGS"
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
    parse_partition_info

    # zephyr.bin already contains a HEADER_SIZE-byte zero placeholder at offset 0
    # (emitted by Zephyr linker via CONFIG_ROM_START_OFFSET). Strip it so that
    # --pad-header does not prepend a second copy, which would push the vector
    # table to slot_addr+2*HEADER_SIZE and cause an immediate hardfault on jump.
    dd if="build/$APP_DIR/zephyr/zephyr.bin" bs=1 skip="$((HEADER_SIZE))" \
        of="build/$APP_DIR/zephyr/zephyr_nohdr.bin" \
        || { rm -f "build/$APP_DIR/zephyr/zephyr_nohdr.bin"; fatal "dd failed to strip header from zephyr.bin"; }

    run_native \
        "imgtool sign --version $VERSION --align 4 --header-size $HEADER_SIZE -S $SLOT_SIZE --pad-header build/$APP_DIR/zephyr/zephyr_nohdr.bin build/$APP_DIR/zephyr/zephyr.prep.bin --custom-tlv 0x00A2 0x03 --custom-tlv 0x00A3 $MODEL_IDENTIFIER && \
         ../bootloader/mcuboot/scripts/imgtool.py dumpinfo ./build/$APP_DIR/zephyr/zephyr.prep.bin > ./build/$APP_DIR/zephyr/dump.txt"

    HASH=$(python ./scripts/extract_hash.py ./build/$APP_DIR/zephyr/dump.txt)
    SIGNATURE0=$(hash_signer -d "$HASH" -s0)
    SIGNATURE1=$(hash_signer -d "$HASH" -s1)
    echo "Signed hash $HASH, signature0 $SIGNATURE0, signature1 $SIGNATURE1"

    run_native \
        "python ./scripts/insert_signatures.py ./build/$APP_DIR/zephyr/zephyr.prep.bin $SIGNATURE0 $SIGNATURE1 -o ./build/$APP_DIR/zephyr/zephyr.signed_trz.bin && \
         python -c \"from intelhex import IntelHex; ih = IntelHex(); ih.loadbin('build/$APP_DIR/zephyr/zephyr.signed_trz.bin', offset=$SLOT_ADDR); ih.tofile('build/$APP_DIR/zephyr/zephyr.signed_trz.hex', format='hex')\" && \
         python ../zephyr/scripts/build/mergehex.py build/mcuboot/zephyr/zephyr.hex build/$APP_DIR/zephyr/zephyr.signed_trz.hex -o build/zephyr.merged.signed_trz.hex"
fi

if [ "$FLASH" -eq 1 ]; then
    run_under_ncs_subshell \
        "west flash --domain \"$APP_DIR\" --hex-file ./build/zephyr.merged.signed_trz.hex"
fi
