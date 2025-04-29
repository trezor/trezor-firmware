#!/usr/bin/env bash
set -e -o pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

############## Select the right Alpine architecture ##############

if [ -z "$ALPINE_ARCH" ]; then
  arch="$(uname -m)"
  case "$arch" in
    aarch64|arm64)
      ALPINE_ARCH="aarch64"
      ;;
    x86_64)
      ALPINE_ARCH="x86_64"
      ;;
    *)
      echo "Unsupported arch"
      exit
  esac
fi

if [ -z "$ALPINE_CHECKSUM" ]; then
  case "$ALPINE_ARCH" in
    aarch64)
      ALPINE_CHECKSUM="1be50ae27c8463d005c4de16558d239e11a88ac6b2f8721c47e660fbeead69bf"
      ;;
    x86_64)
      ALPINE_CHECKSUM="ec7ec80a96500f13c189a6125f2dbe8600ef593b87fc4670fe959dc02db727a2"
      ;;
    *)
      exit
  esac
 fi


DOCKER=${DOCKER:-docker}
CONTAINER_NAME=${CONTAINER_NAME:-trezor-firmware-env.nix}
ALPINE_CDN=${ALPINE_CDN:-https://dl-cdn.alpinelinux.org/alpine}
ALPINE_RELEASE=${ALPINE_RELEASE:-3.15}
ALPINE_VERSION=${ALPINE_VERSION:-3.15.0}
ALPINE_TARBALL=${ALPINE_FILE:-alpine-minirootfs-$ALPINE_VERSION-$ALPINE_ARCH.tar.gz}
NIX_VERSION=${NIX_VERSION:-2.4}
CONTAINER_FS_URL=${CONTAINER_FS_URL:-"$ALPINE_CDN/v$ALPINE_RELEASE/releases/$ALPINE_ARCH/$ALPINE_TARBALL"}

############## Options parsing ##############

function help_and_die() {
  echo "Usage: $0 [options] tag"
  echo "Options:"
  echo "  --skip-bitcoinonly - do not build bitcoin-only firmwares"
  echo "  --skip-normal - do not build regular firmwares"
  echo "  --repository path/to/repo - checkout the repository from the given path/url"
  echo "  --no-init - do not recreate docker environments"
  echo "  --models - comma-separated list of models. default: --models T1B1,T2B1,T2T1,T3T1"
  echo "  --targets - comma-separated list of targets for core build. default: --targets boardloader,bootloader,firmware"
  echo "  --help"
  echo
  echo "Option --prodtest is deprecated. Use "--targets prodtest" to build prodtest."
  echo "Set PRODUCTION=0 to run non-production builds."
  echo "Set VENDOR_HEADER=vendorheader_prodtest_unsigned.bin to use the specified vendor header for prodtest."
  exit 0
}

OPT_BUILD_NORMAL=1
OPT_BUILD_BITCOINONLY=1
INIT=1
MODELS=(T1B1 T2B1 T2T1 T3T1)
CORE_TARGETS=(boardloader bootloader firmware)

REPOSITORY="file:///local"

while true; do
  case "$1" in
    -h|--help)
      help_and_die
      ;;
    --skip-bitcoinonly)
      OPT_BUILD_BITCOINONLY=0
      shift
      ;;
    --skip-normal)
      OPT_BUILD_NORMAL=0
      shift
      ;;
    --repository)
      REPOSITORY="$2"
      shift 2
      ;;
    --no-init)
      INIT=0
      shift
      ;;
    --models)
      # take comma-separated next argument and turn it into an array
      IFS=',' read -r -a MODELS <<< "$2"
      shift 2
      ;;
    --targets)
      # take comma-separated next argument and turn it into an array
      IFS=',' read -r -a CORE_TARGETS <<< "$2"
      shift 2
      ;;
    *)
      break
      ;;
  esac
done

if [ -z "$1" ]; then
  help_and_die
fi

################## Variant selection ##################

variants=()
if [ "$OPT_BUILD_NORMAL" -eq 1 ]; then
  variants+=(0)
fi
if [ "$OPT_BUILD_BITCOINONLY" -eq 1 ]; then
  variants+=(1)
fi

VARIANTS=("${variants[@]}")

TAG="$1"
COMMIT_HASH="$(git rev-parse "$TAG")"
PRODUCTION=${PRODUCTION:-1}

if which wget > /dev/null ; then
  wget --no-config -nc -P ci/ "$CONTAINER_FS_URL"
else
  if ! [ -f "ci/$ALPINE_TARBALL" ]; then
    curl -L -o "ci/$ALPINE_TARBALL" "$CONTAINER_FS_URL"
  fi
fi

# check alpine checksum
if command -v shasum &> /dev/null ; then
    echo "${ALPINE_CHECKSUM}  ci/${ALPINE_TARBALL}" | shasum -a 256 -c
else
    echo "${ALPINE_CHECKSUM}  ci/${ALPINE_TARBALL}" | sha256sum -c
fi

tag_clean="${TAG//[^a-zA-Z0-9]/_}"
SNAPSHOT_NAME="${CONTAINER_NAME}__${tag_clean}"

mkdir -p build/core build/legacy
mkdir -p build/core-bitcoinonly build/legacy-bitcoinonly

# if not initializing, does the image exist?
if [ $INIT -eq 0 ] && ! $DOCKER image inspect $SNAPSHOT_NAME > /dev/null; then
  echo "Image $SNAPSHOT_NAME does not exist."
  exit 1
fi

GIT_CLEAN_REPO="git clean -dfx -e .venv"
SCRIPT_NAME="._setup_script"

if [ $INIT -eq 1 ]; then

  SELECTED_CONTAINER="$CONTAINER_NAME"

  echo
  echo ">>> DOCKER BUILD ALPINE_VERSION=$ALPINE_VERSION ALPINE_ARCH=$ALPINE_ARCH NIX_VERSION=$NIX_VERSION -t $CONTAINER_NAME"
  echo

  # some Nix installations have problem with shell.nix -> ci/shell.nix symlink
  # docker can't handle ci/shell.nix -> shell.nix
  # let's copy the file and try to fix paths ...
  sed "s|./ci/|./|" < shell.nix > ci/shell.nix

  $DOCKER build \
    --network=host \
    --build-arg ALPINE_VERSION="$ALPINE_VERSION" \
    --build-arg ALPINE_ARCH="$ALPINE_ARCH" \
    --build-arg NIX_VERSION="$NIX_VERSION" \
    -t "$CONTAINER_NAME" \
    ci/

  cat <<EOF > "$SCRIPT_NAME"
    #!/bin/bash
    set -e -o pipefail

    mkdir -p /reproducible-build
    cd /reproducible-build
    # ignore ownership of the local repo
    git config --global --add safe.directory /local/.git
    git clone --branch="$TAG" --depth=1 "$REPOSITORY" trezor-firmware
    cd trezor-firmware
EOF

else  # init == 0

  SELECTED_CONTAINER="$SNAPSHOT_NAME"

  cat <<EOF > "$SCRIPT_NAME"
    #!/bin/bash
    set -e -o pipefail

    cd /reproducible-build/trezor-firmware
EOF

fi  # init

# append common part to script
cat <<EOF >> "$SCRIPT_NAME"
  $GIT_CLEAN_REPO
  git submodule update --init --recursive
  poetry install -v --no-ansi --no-interaction
  cd core/embed/rust
  cargo fetch

  echo
  echo ">>> AT COMMIT \$(git rev-parse HEAD)"
  echo
EOF

echo
echo ">>> DOCKER REFRESH $SNAPSHOT_NAME"
echo

$DOCKER run \
  --network=host \
  -t \
  -v "$PWD:/local" \
  -v "$PWD/build:/build" \
  --name "$SNAPSHOT_NAME" \
  "$SELECTED_CONTAINER" \
  /nix/var/nix/profiles/default/bin/nix-shell --run "bash /local/$SCRIPT_NAME" \
  || ($DOCKER rm "$SNAPSHOT_NAME"; exit 1)

rm $SCRIPT_NAME

echo
echo ">>> DOCKER COMMIT $SNAPSHOT_NAME"
echo

$DOCKER commit "$SNAPSHOT_NAME" "$SNAPSHOT_NAME"
$DOCKER rm "$SNAPSHOT_NAME"

# stat under macOS has slightly different cli interface
USER=$(stat -c "%u" . 2>/dev/null || stat -f "%u" .)
GROUP=$(stat -c "%g" . 2>/dev/null || stat -f "%g" .)

DIR=$(pwd)

# build core

for TREZOR_MODEL in ${MODELS[@]}; do
  if [ "$TREZOR_MODEL" = "T1B1" ]; then
    continue
  fi
  for BITCOIN_ONLY in ${VARIANTS[@]}; do

    DIRSUFFIX=${BITCOIN_ONLY/1/-bitcoinonly}
    DIRSUFFIX=${DIRSUFFIX/0/}
    DIRSUFFIX="-${TREZOR_MODEL}${DIRSUFFIX}"

    MAKE_TARGETS=""
    for TARGET in ${CORE_TARGETS[@]}; do
      MAKE_TARGETS="$MAKE_TARGETS build_$TARGET"
    done

    SCRIPT_NAME=".build_core_${TREZOR_MODEL}_${BITCOIN_ONLY}.sh"
    cat <<EOF > "build/$SCRIPT_NAME"
      # DO NOT MODIFY!
      # this file was generated by ${BASH_SOURCE[0]}
      # variant: core build BITCOIN_ONLY=$BITCOIN_ONLY TREZOR_MODEL=$TREZOR_MODEL
      set -e -o pipefail
      cd /reproducible-build/trezor-firmware/core
      $GIT_CLEAN_REPO
      poetry run make clean vendor $MAKE_TARGETS QUIET_MODE=1
      for item in bootloader firmware prodtest; do
        if [ -f build/\$item/\$item.bin ]; then
          poetry run ../python/tools/firmware-fingerprint.py \
                      -o build/\$item/\$item.bin.fingerprint \
                      build/\$item/\$item.bin
        fi
      done
      rm -rf /build/*
      cp -r build/* /build
      chown -R $USER:$GROUP /build
EOF

    echo
    echo ">>> DOCKER RUN core BITCOIN_ONLY=$BITCOIN_ONLY TREZOR_MODEL=$TREZOR_MODEL PRODUCTION=$PRODUCTION"
    echo "    (targets: ${CORE_TARGETS[@]})"
    echo

    $DOCKER run \
      --network=host \
      --rm \
      -v "$DIR:/local" \
      -v "$DIR/build/core$DIRSUFFIX":/build:z \
      --env BITCOIN_ONLY="$BITCOIN_ONLY" \
      --env TREZOR_MODEL="$TREZOR_MODEL" \
      --env PRODUCTION="$PRODUCTION" \
      --env VENDOR_HEADER="$VENDOR_HEADER" \
      --init \
      "$SNAPSHOT_NAME" \
      /nix/var/nix/profiles/default/bin/nix-shell --run "bash /local/build/$SCRIPT_NAME"
  done
done

# build legacy

if echo "${MODELS[@]}" | grep -q T1B1 ; then
  for BITCOIN_ONLY in ${VARIANTS[@]}; do

    DIRSUFFIX=${BITCOIN_ONLY/1/-bitcoinonly}
    DIRSUFFIX=${DIRSUFFIX/0/}
    DIRSUFFIX="-T1B1${DIRSUFFIX}"

    SCRIPT_NAME=".build_legacy_$BITCOIN_ONLY.sh"
    cat <<EOF > "build/$SCRIPT_NAME"
      # DO NOT MODIFY!
      # this file was generated by ${BASH_SOURCE[0]}
      # variant: legacy build BITCOIN_ONLY=$BITCOIN_ONLY
      set -e -o pipefail
      cd /reproducible-build/trezor-firmware/legacy
      $GIT_CLEAN_REPO
      ln -s /build build
      poetry run script/cibuild
      mkdir -p build/bootloader build/firmware build/intermediate_fw
      cp bootloader/bootloader.bin build/bootloader/bootloader.bin
      cp intermediate_fw/trezor.bin build/intermediate_fw/inter.bin
      cp firmware/trezor.bin build/firmware/firmware.bin
      cp firmware/firmware*.bin build/firmware/ || true  # ignore missing file as it will not be present in old tags
      cp firmware/trezor.elf build/firmware/firmware.elf
      poetry run ../python/tools/firmware-fingerprint.py \
                 -o build/firmware/firmware.bin.fingerprint \
                 build/firmware/firmware.bin
      chown -R $USER:$GROUP /build
EOF

    echo
    echo ">>> DOCKER RUN legacy BITCOIN_ONLY=$BITCOIN_ONLY PRODUCTION=$PRODUCTION"
    echo

    $DOCKER run \
      --network=host \
      --rm \
      -v "$DIR:/local" \
      -v "$DIR/build/legacy$DIRSUFFIX":/build:z \
      --env BITCOIN_ONLY="$BITCOIN_ONLY" \
      --env PRODUCTION="$PRODUCTION" \
      --init \
      "$SNAPSHOT_NAME" \
      /nix/var/nix/profiles/default/bin/nix-shell --run "bash /local/build/$SCRIPT_NAME"
  done
fi

echo
echo "Docker image retained as $SNAPSHOT_NAME"
echo "To remove it, run:"
echo "  docker rmi $SNAPSHOT_NAME"

# all built, show fingerprints

echo
echo "Built from commit $COMMIT_HASH"
echo
echo "Fingerprints:"
for VARIANT in core legacy; do
  for MODEL in ${MODELS[@]}; do
    for DIRSUFFIX in "" "-bitcoinonly"; do
      BUILD_DIR=build/${VARIANT}-${MODEL}${DIRSUFFIX}
      for file in $BUILD_DIR/*/*.fingerprint; do
        if [ -f "$file" ]; then
          origfile="${file%.fingerprint}"
          fingerprint=$(tr -d '\n' < $file)
          echo "$fingerprint $origfile"
        fi
      done
    done
  done
done
