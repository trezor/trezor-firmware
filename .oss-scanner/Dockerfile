# Build environment for Anthropic's OSS Scanner (https://github.com/anthropics/oss-scanner).
#
# The scanner builds this file with the repository checkout as the build context, with network access. The
# resulting image is then analysed offline, so everything needed to build and test must be fetched here.
#
# The toolchain comes from shell.nix and the Python environment from uv, as in local development (see
# AGENTS.md). The nix-shell environment is dumped into /etc/trezor-firmware-env.sh, which every bash shell
# sources (via BASH_ENV and ~/.bashrc), so `xtask`, `make`, `pytest`, `trezorctl` etc. work without entering
# nix-shell. The prebuilt emulator is T3T1 with the `test-live` preset: non-frozen with debuglink, so it runs
# both the core unit tests and the device tests, and picks up Python edits in core/src without rebuilding.
#
# To try it locally: docker build -f .oss-scanner/Dockerfile -t trezor-oss-scanner .

# Debian, because the scanner adds its own layer (Claude Code, gdb, valgrind, ...) with a package manager. Its
# glibc must not be older than the one the nix-shell libraries on LD_LIBRARY_PATH need (bookworm's is too old).
FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git procps python3 xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Single-user Nix as root, same version as ci/Dockerfile.
ARG NIX_VERSION=2.31.4
RUN arch="$(uname -m)"; \
    case "$arch" in \
      x86_64) sha256=a21fde5116b1f28ef4990cc9fdb2b5002cff43bbd85171e199f2e72b7fc0b9fa ;; \
      aarch64) sha256=3fdef0c5638853dc78136d27583984e42d16d5e9c1d9569eb0fbec8aed966daf ;; \
      *) echo "unsupported architecture: $arch"; exit 1 ;; \
    esac; \
    tarball="nix-${NIX_VERSION}-${arch}-linux"; \
    curl -fsSL -o "/tmp/$tarball.tar.xz" "https://releases.nixos.org/nix/nix-${NIX_VERSION}/$tarball.tar.xz" \
    && echo "$sha256  /tmp/$tarball.tar.xz" | sha256sum -c - \
    && tar -xJf "/tmp/$tarball.tar.xz" -C /tmp \
    && mkdir -m 0755 /etc/nix /nix \
    && printf 'sandbox = false\nbuild-users-group =\n' > /etc/nix/nix.conf \
    && USER=root "/tmp/$tarball/install" --no-daemon --no-channel-add --no-modify-profile \
    && rm -rf "/tmp/$tarball" "/tmp/$tarball.tar.xz"

ENV USER=root \
    PATH=/nix/var/nix/profiles/default/bin:/root/.nix-profile/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    NIX_SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Realize the nix-shell environment and dump it into a sourceable script. Variables specific to the nix-shell
# session (temp dirs, shell bookkeeping) are left out. Only shell.nix is copied, so this layer is cached
# across source changes.
COPY shell.nix /opt/trezor-firmware-env/shell.nix
RUN nix-shell /opt/trezor-firmware-env/shell.nix --run ' \
      for v in $(compgen -e); do \
        case "$v" in \
          HOME|PWD|OLDPWD|SHLVL|TMP|TMPDIR|TEMP|TEMPDIR|NIX_BUILD_TOP|TERM|HOSTNAME|USER|LOGNAME|SHELL|_|NIX_LOG_FD|NIX_REMOTE|SSL_CERT_FILE|NIX_SSL_CERT_FILE) continue ;; \
        esac; \
        printf "export %s=%q\n" "$v" "${!v}"; \
      done' > /etc/trezor-firmware-env.sh \
    && printf '%s\n' \
      'export VIRTUAL_ENV=/src/.venv' \
      'export PATH="/src/.venv/bin:$PATH"' \
      >> /etc/trezor-firmware-env.sh

# scanner contract: the checkout lives inside the image, at /src
COPY . /src
WORKDIR /src

# The scanner clones the repository without submodules.
RUN . /etc/trezor-firmware-env.sh \
    && git config --global --add safe.directory '*' \
    && git submodule update --init --recursive --depth 1 --jobs 8

# Python deps, and all Rust crates of the core workspace, so that later builds work offline.
RUN . /etc/trezor-firmware-env.sh \
    && uv sync --locked \
    && cargo fetch --locked --manifest-path core/embed/Cargo.toml

# T3T1 emulator with debuglink, non-frozen. Artifacts land in core/build/artifacts/T3T1/ (`latest` symlink).
RUN . /etc/trezor-firmware-env.sh \
    && xtask build firmware --emulator -m T3T1 -p test-live

# Host-side builds of the crypto library and its tests (crypto/tests/test_check etc., with ASAN and UBSAN), and
# of the storage test libraries.
RUN . /etc/trezor-firmware-env.sh \
    && ADDRESS_SANITIZER=1 make -C crypto -j"$(nproc)" \
    && make -C storage/tests build

# From here on, every bash shell (interactive or not) gets the environment, and tools do not try the network.
# ASAN_OPTIONS as in CI (.github/workflows/common.yml): the crypto pytest suite loads the ASAN-built
# libtrezor-crypto.so into an uninstrumented python via ctypes, which fails without verify_asan_link_order=0.
RUN printf '%s\n' \
      'export UV_OFFLINE=1' \
      'export CARGO_NET_OFFLINE=true' \
      'export ASAN_OPTIONS=verify_asan_link_order=0:detect_leaks=0' \
      >> /etc/trezor-firmware-env.sh \
    && echo '. /etc/trezor-firmware-env.sh' >> /root/.bashrc
ENV BASH_ENV=/etc/trezor-firmware-env.sh

# Run the cheap tests so we know the image works, but do not let a failure abort the build.
RUN (timeout 900 make -C core test || echo "WARNING: core unit tests reported failures") \
    && (timeout 600 ./core/emu.py -h -t -P 30000 -q -c pytest tests/device_tests -k test_msg_ping \
        || echo "WARNING: device test smoke run failed")
