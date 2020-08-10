# install the latest Alpine linux from scratch

FROM scratch
ARG ALPINE_VERSION=3.12.0
ADD alpine-minirootfs-${ALPINE_VERSION}-x86_64.tar.gz /

# the following is adapted from https://github.com/NixOS/docker/blob/master/Dockerfile

# Enable HTTPS support in wget and set nsswitch.conf to make resolution work within containers
RUN apk add --no-cache --update openssl \
  && echo hosts: dns files > /etc/nsswitch.conf

# Download Nix and install it into the system.
ARG NIX_VERSION=2.3.6
RUN wget https://nixos.org/releases/nix/nix-${NIX_VERSION}/nix-${NIX_VERSION}-x86_64-linux.tar.xz \
  && tar xf nix-${NIX_VERSION}-x86_64-linux.tar.xz \
  && addgroup -g 30000 -S nixbld \
  && for i in $(seq 1 30); do adduser -S -D -h /var/empty -g "Nix build user $i" -u $((30000 + i)) -G nixbld nixbld$i ; done \
  && mkdir -m 0755 /etc/nix \
  && echo 'sandbox = false' > /etc/nix/nix.conf \
  && mkdir -m 0755 /nix && USER=root sh nix-${NIX_VERSION}-x86_64-linux/install \
  && ln -s /nix/var/nix/profiles/default/etc/profile.d/nix.sh /etc/profile.d/ \
  && rm -r /nix-${NIX_VERSION}-x86_64-linux* \
  && rm -rf /var/cache/apk/* \
  && /nix/var/nix/profiles/default/bin/nix-collect-garbage --delete-old \
  && /nix/var/nix/profiles/default/bin/nix-store --optimise \
  && /nix/var/nix/profiles/default/bin/nix-store --verify --check-contents

ENV \
    USER=root \
    PATH=/nix/var/nix/profiles/default/bin:/nix/var/nix/profiles/default/sbin:/bin:/sbin:/usr/bin:/usr/sbin \
    GIT_SSL_CAINFO=/etc/ssl/certs/ca-certificates.crt \
    NIX_SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    NIX_PATH=/nix/var/nix/profiles/per-user/root/channels

# Trezor specific stuff starts here

COPY shell.nix shell.nix

RUN nix-shell --run "echo deps pre-installed"

CMD [ "nix-shell" ]

# the rest of the file only applies when docker build is called
# with the following argument: "--build-arg FULLDEPS_TESTING=1"

ARG FULLDEPS_TESTING=0
ENV FULLDEPS_TESTING=${FULLDEPS_TESTING}

# install other python versions for tox testing

RUN if [ "${FULLDEPS_TESTING}" = "1" ]; then \
        nix-env -iP python3-3.7.7 ; \
        nix-env --set-flag priority 6 python3-3.7.7 ; \
        nix-env -iP python3-3.6.10 ; \
        nix-env --set-flag priority 7 python3-3.6.10 ; \
        nix-env -iP python3-3.5.9 ; \
        nix-env --set-flag priority 8 python3-3.5.9 ; \
    fi

# download monero tests binary

ENV TREZOR_MONERO_TESTS_PATH="/opt/trezor_monero_tests"
RUN if [ "${FULLDEPS_TESTING}" = "1" ]; then \
        TREZOR_MONERO_TESTS_SHA256SUM=1e5dfdb07de4ea46088f4a5bdb0d51f040fe479019efae30f76427eee6edb3f7 ; \
        TREZOR_MONERO_TESTS_URL="https://github.com/ph4r05/monero/releases/download/v0.15.0.0-tests-u18.04-03/trezor_tests" ; \
        wget --no-verbose "${TREZOR_MONERO_TESTS_URL}" -O "${TREZOR_MONERO_TESTS_PATH}" ; \
        chmod +x "${TREZOR_MONERO_TESTS_PATH}" ; \
        echo "${TREZOR_MONERO_TESTS_SHA256SUM} ${TREZOR_MONERO_TESTS_PATH}" | sha256sum -c ; \
        nix-shell -p patchelf --run 'patchelf --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" "${TREZOR_MONERO_TESTS_PATH}"' ; \
    fi
