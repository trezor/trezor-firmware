#!/bin/bash

# Script builds, signs, and/or flashes Nordic board with optional debug or production overlays

# Run this in `nordic/trezor` to sign and mergehex final image with mcuboot
# This charade serves to differentiate commands run under uv shell and ncs shell since their pythons are not compatible

# Update the OPTSTRING to include 'a:'
OPTSTRING=":b:a:i:pdsfc"

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
# MCUboot child-image Kconfig fragments (names under <app>/sysbuild/), assembled
# from -d/-p and then extended per board -- see the BOARD block.
MCUBOOT_CONFS=
# Optional founder-signed app image to merge/flash instead of the bare build output.
# The literal "auto" means "resolve it from the trezor-firmware bundle" (-i with no
# path argument).
SIGNED_IMAGE=
# Decoded from CONFIG_MODEL_IDENTIFIER by parse_partition_info (e.g. "T3W1"), so the
# trezor-firmware paths below work even when -s runs without -b.
MODEL_NAME=
# trezor-firmware core/, relative to nordic/trezor where this script is run.
CORE_DIR="../../core"
# "legacy" or "founder" -- which signing scheme this model's MCUboot verifies.
# Resolved from the build (see resolve_sign_variant), never passed in.
SIGN_VARIANT=
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

# Run host-side layout/merge tools in the *current* shell. imgtool and the helper
# Python scripts come from the uv/.venv (or nix) environment and
# must NOT inherit the NCS toolchain's Python env (PYTHONHOME), which points a
# different-version interpreter at the wrong stdlib ("SRE module mismatch").
# Only 'west build'/'west flash' need the NCS toolchain (run_under_ncs_subshell).
run_native() {
    eval "$@" || fatal "Error running host command: $*"
}

usage() {
    echo "$0 [-b board_name] [-a app_dir] [-i signed_image] [-p] [-d] [-c] [-s] [-f]"
    cat <<END
    Parameters:
    -b board: full board target (e.g. t3t2_dk/nrf54ls05b/cpuapp) or a model
              alias (t3t2, t3w1) that expands to that model's default board
    -a app_dir: specify application directory (default: trezor-ble)
    -i [image]: merge/flash a FOUNDER-SIGNED app image instead of the bare build
                output. With no path, takes it from the trezor-firmware bundle:
                  core/build-xtask/tree/<MODEL>/trezor-ble[-dev].bin
                Use with -s (and -f to flash). Without -i the BARE app is merged,
                which this MCUboot rejects -- which is what you want to install a
                new MCUboot, or to force the OTA push.
    -p: production build
    -d: use debug overlay when building
    -c: clean build (pristine)
    -s: lay out the app image (and, on -d builds, copy it to
        core/embed/models/<MODEL>/ for founder signing)
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

    # Same bytes, as ASCII -- names the trezor-firmware model folder. Taken from the
    # BUILD rather than from -b so it is still right when signing in a separate
    # invocation (and cannot disagree with what was actually built).
    MODEL_NAME=$(printf "\\x${hex:6:2}\\x${hex:4:2}\\x${hex:2:2}\\x${hex:0:2}")
    case "$MODEL_NAME" in
        [A-Z][0-9A-Z][0-9A-Z][0-9A-Z]) ;;
        *) fatal "could not decode a model name from CONFIG_MODEL_IDENTIFIER (got '$MODEL_NAME')" ;;
    esac
}

# Which signing scheme the model's MCUboot expects. This follows the SDK, which is
# pinned per board (see verify_environment) because a published model cannot change
# SDK for certification reasons:
#
#   T3W1  NCS 2.9  mcuboot trezor-v2.1.0-ncs3   LEGACY: two Ed25519 signatures over
#                                               the image hash (TLVs 0x00A0/0x00A1),
#                                               against the nRF's own key pool.
#   T3T2  NCS 3.3  mcuboot trezor-ncs3.3.0      FOUNDER: post-quantum founder Merkle
#                                               tree (CONFIG_BOOT_PQ_SECURE_BOOT); the
#                                               image carries no signature of its own.
#
# Derived from the BUILD (MODEL_NAME) rather than from -b, so it cannot disagree with
# what was actually built, and still works when -s runs in a separate invocation.
resolve_sign_variant() {
    case "$MODEL_NAME" in
        T3W1) SIGN_VARIANT="legacy" ;;
        T3T2) SIGN_VARIANT="founder" ;;
        *)    fatal "model '$MODEL_NAME' has no known signing variant; add it to resolve_sign_variant()" ;;
    esac
    echo "signing variant: $SIGN_VARIANT (model $MODEL_NAME)"
}

# Name of this model's committed/bundled nRF image. Dev builds (-d) use the -dev
# variant, matching trezor-firmware's default_nrf_image().
nrf_image_name() {
    if [ -n "$DEBUG" ]; then echo "trezor-ble-dev.bin"; else echo "trezor-ble.bin"; fi
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
    i)
      # Optional argument. getopts always grabs the next word for "i:", so if that
      # word is actually the next option, hand it back and fall through to "auto".
      case "$OPTARG" in
        -*) OPTIND=$((OPTIND - 1)); SIGNED_IMAGE="auto" ;;
        *)  SIGNED_IMAGE="$OPTARG" ;;
      esac
      ;;
    c)
      # Force a full wipe (not 'auto'): switching SDK/toolchain leaves a
      # CMakeCache.txt with stale toolchain paths (ninja, zephyr-sdk) that 'auto'
      # will not detect because the board is unchanged.
      PRISTINE="--pristine=always"
      ;;
    d)
      DEBUG="-DOVERLAY_CONFIG=debug.conf"
      MCUBOOT_CONFS="mcuboot.conf;mcuboot_debug.conf"
      ;;
    p)
      PRODUCTION="-DOVERLAY_CONFIG=prod.conf"
      MCUBOOT_CONFS="mcuboot.conf;mcuboot_prod.conf"
      ;;
    s)
      SIGN=1
      ;;
    f)
      FLASH=1
      ;;
    :)
      # Missing argument. For -i that is legitimate ("use the bundle's image");
      # anything else is a usage error.
      if [ "$OPTARG" = "i" ]; then
        SIGNED_IMAGE="auto"
      else
        echo "option -$OPTARG requires an argument"
        usage
        exit 2
      fi
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
        t3t2_dk*)
            SB_OVERLAY="-DSB_EXTRA_CONF_FILE=$PWD/$APP_DIR/sysbuild_nrf54l.conf"
            # Founder-tree (post-quantum) verification is NCS 3.3 / nRF54L only:
            # CONFIG_BOOT_PQ_SECURE_BOOT does not exist in the NCS 2.9 MCUboot
            # revision, and assigning an undefined symbol aborts the Kconfig run.
            # T3W1 stays on 2.9 (certification) with the legacy signing scheme.
            MCUBOOT_CONFS="${MCUBOOT_CONFS:-mcuboot.conf};mcuboot_t3t2.conf"
            ;;
    esac

    # Expand the fragment names to absolute paths for -Dmcuboot_EXTRA_CONF_FILE.
    MCUBOOT_ARG=
    if [ -n "$MCUBOOT_CONFS" ]; then
        _confs=
        IFS=';' read -ra _names <<< "$MCUBOOT_CONFS"
        for _n in "${_names[@]}"; do
            [ -f "$APP_DIR/sysbuild/$_n" ] || fatal "missing mcuboot fragment: $APP_DIR/sysbuild/$_n"
            _confs="${_confs:+$_confs;}$PWD/$APP_DIR/sysbuild/$_n"
        done
        MCUBOOT_ARG="-Dmcuboot_EXTRA_CONF_FILE=\"$_confs\""
        echo "mcuboot config: $MCUBOOT_CONFS"
    fi

    # Assemble all post-'--' cmake args; emit the '--' separator only if any exist.
    EXTRA_CMAKE_ARGS="$DEBUG $PRODUCTION $SB_OVERLAY $MCUBOOT_ARG"
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
# Hand the laid-out app image to trezor-firmware, which commits it as this model's
# model-tree leaf AND embeds it in the coreapp (firmware/build.rs reads the same
# path). Dev builds only: -dev is the image a --bootloader-devel bundle picks up,
# and production signing is a separate, deliberate flow we should not stage into
# silently.
stage_for_signing() {
    [ -n "$DEBUG" ] || return 0
    local model_dir="$CORE_DIR/embed/models/$MODEL_NAME"
    if [ ! -d "$model_dir" ]; then
        echo "note: $model_dir not found; skipping the copy for signing"
        return 0
    fi
    cp "build/$APP_DIR/zephyr/zephyr.trz.bin" "$model_dir/$(nrf_image_name)" \
        || fatal "failed to copy the image into $model_dir"
    echo "copied for signing -> $model_dir/$(nrf_image_name)"
}


    resolve_sign_variant

    if [ "$SIGN_VARIANT" = "legacy" ]; then
        # LEGACY (NCS 2.9 / T3W1): imgtool lays out the image and computes the
        # image-hash TLV; the two Trezor Ed25519 signatures over that hash are
        # inserted afterwards (TLVs 0x00A0/0x00A1) and verified by MCUboot against
        # the nRF's OWN key pool. 0x00A2 names which of those keys signed, 0x00A3
        # pins the model; both are PROTECTED, so covered by the image hash.
        run_native \
            "imgtool sign --version $VERSION --align 4 --header-size $HEADER_SIZE -S $SLOT_SIZE --pad-header build/$APP_DIR/zephyr/zephyr_nohdr.bin build/$APP_DIR/zephyr/zephyr.prep.bin --custom-tlv 0x00A2 0x03 --custom-tlv 0x00A3 $MODEL_IDENTIFIER && \
             ../bootloader/mcuboot/scripts/imgtool.py dumpinfo ./build/$APP_DIR/zephyr/zephyr.prep.bin > ./build/$APP_DIR/zephyr/dump.txt"

        HASH=$(python ./scripts/extract_hash.py ./build/$APP_DIR/zephyr/dump.txt)
        SIGNATURE0=$(hash_signer -d "$HASH" -s0)
        SIGNATURE1=$(hash_signer -d "$HASH" -s1)
        echo "Signed hash $HASH, signature0 $SIGNATURE0, signature1 $SIGNATURE1"

        run_native \
            "python ./scripts/insert_signatures.py ./build/$APP_DIR/zephyr/zephyr.prep.bin $SIGNATURE0 $SIGNATURE1 -o ./build/$APP_DIR/zephyr/zephyr.trz.bin"
        echo "nRF app image (legacy-signed): build/$APP_DIR/zephyr/zephyr.trz.bin"
        [ -z "$SIGNED_IMAGE" ] || echo "note: -i is ignored for the legacy variant (the image is signed here)"
        SIGNED_IMAGE=
        # Fully signed already -- nothing to hand back for founder signing, but the
        # tree build and the coreapp still read it from models/, so stage it. This
        # used to live only on the founder path, which left the legacy image with no
        # way to reach the tree at all.
        stage_for_signing
        echo "next: (cd $CORE_DIR && make build_pq TREZOR_MODEL=$MODEL_NAME)"
    else
        # FOUNDER (NCS 3.3 / T3T2): no signature of its own. imgtool only lays out
        # the image and computes the image-hash TLV; authenticity comes from the
        # founder Merkle tree, the SAME signature the Trezor STM boot header carries
        # over modelRoot (SLH-DSA + Ed25519 hybrid, 2-of-3). Both custom TLVs are
        # PROTECTED, hence inside the founder leaf:
        #   0x00A2 sigmask  -- PLACEHOLDER (0x00). The value is the SIGNER's to
        #                      choose; trezor-firmware stamps it (re-stamping the
        #                      image hash, which protected TLVs are part of) before
        #                      computing the leaf. Keeping it out of the build is what
        #                      makes founder key rotation a re-sign, not a rebuild.
        #   0x00A3 model id -- pins the image to this model
        run_native \
            "imgtool sign --version $VERSION --align 4 --header-size $HEADER_SIZE -S $SLOT_SIZE --pad-header build/$APP_DIR/zephyr/zephyr_nohdr.bin build/$APP_DIR/zephyr/zephyr.prep.bin --custom-tlv 0x00A2 0x00 --custom-tlv 0x00A3 $MODEL_IDENTIFIER && \
             ../bootloader/mcuboot/scripts/imgtool.py dumpinfo ./build/$APP_DIR/zephyr/zephyr.prep.bin > ./build/$APP_DIR/zephyr/dump.txt"

        # -i with no path: take the founder-signed image from the trezor-firmware
        # bundle for this model.
        if [ "$SIGNED_IMAGE" = "auto" ]; then
            SIGNED_IMAGE="$CORE_DIR/build-xtask/tree/$MODEL_NAME/$(nrf_image_name)"
            echo "-i: using the signed image from the bundle: $SIGNED_IMAGE"
            [ -f "$SIGNED_IMAGE" ] || fatal "-i: $SIGNED_IMAGE not found.
Sign it first, from trezor-firmware/core:
    make build_pq TREZOR_MODEL=$MODEL_NAME TREE_OPTS=\"--nrf-pq-native\""
        fi

        # Which app image ends up in the merged hex:
        #
        #   default   the BARE image -- this MCUboot REJECTS it, so the nRF waits in
        #             serial recovery until the STM pushes a founder-signed image over
        #             OTA. Useful to install a new MCUboot, and to force the OTA push
        #             (the STM sees no valid nRF app, so it cannot skip the update).
        #
        #   -i [img]  the FOUNDER-SIGNED image, so the nRF boots straight away. Use
        #             this to test the nRF's own founder verification without OTA.
        #             The STM will then SKIP the push, since the running nRF already
        #             matches the bundle's image hash.
        if [ -n "$SIGNED_IMAGE" ]; then
            [ -f "$SIGNED_IMAGE" ] || fatal "-i: no such file: $SIGNED_IMAGE"
            img_size=$(wc -c < "$SIGNED_IMAGE")
            [ "$img_size" -le "$((SLOT_SIZE))" ] \
                || fatal "-i: image is $img_size B, slot0 is $((SLOT_SIZE)) B"
            cp "$SIGNED_IMAGE" "build/$APP_DIR/zephyr/zephyr.trz.bin" \
                || fatal "failed to stage $SIGNED_IMAGE"
            echo "nRF app image (founder-signed, from $SIGNED_IMAGE): $img_size B"
        else
            cp "build/$APP_DIR/zephyr/zephyr.prep.bin" "build/$APP_DIR/zephyr/zephyr.trz.bin" \
                || fatal "failed to stage zephyr.trz.bin"
            echo "nRF app image (BARE, founder material pending -- MCUboot will reject it):"
            echo "  build/$APP_DIR/zephyr/zephyr.trz.bin"

            # Hand the bare image straight to trezor-firmware for founder signing.
            # Dev builds only: -dev is the image trezor-firmware picks up for a
            # --bootloader-devel bundle, and production signing is a separate,
            # deliberate flow we should not stage into silently.
            stage_for_signing
            if [ -n "$DEBUG" ]; then
                echo "next: (cd $CORE_DIR && make build_pq TREZOR_MODEL=$MODEL_NAME \
TREE_OPTS=\"--nrf-pq-native\") && $0 -b <board> -d -s -f -i"
            fi
        fi
    fi

    run_native \
        "python -c \"from intelhex import IntelHex; ih = IntelHex(); ih.loadbin('build/$APP_DIR/zephyr/zephyr.trz.bin', offset=$SLOT_ADDR); ih.tofile('build/$APP_DIR/zephyr/zephyr.trz.hex', format='hex')\" && \
         python ../zephyr/scripts/build/mergehex.py build/mcuboot/zephyr/zephyr.hex build/$APP_DIR/zephyr/zephyr.trz.hex -o build/zephyr.merged.trz.hex"
fi

if [ "$FLASH" -eq 1 ]; then
    run_under_ncs_subshell \
        "west flash --domain \"$APP_DIR\" --hex-file ./build/zephyr.merged.trz.hex"
fi
