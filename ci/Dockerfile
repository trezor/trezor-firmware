FROM nixos/nix:2.3.4

COPY shell.nix shell.nix

RUN nix-env -i -f shell.nix -A buildInputs

CMD [ "nix-shell" ]

# the rest of the file only applies when docker build is called
# with the following argument: "--build-arg FULLDEPS_TESTING=1"

ENV TREZOR_MONERO_TESTS_PATH="/opt/trezor_monero_tests"

ARG FULLDEPS_TESTING=0
ENV FULLDEPS_TESTING=${FULLDEPS_TESTING}

# install other python versions for tox testing

RUN if [ "${FULLDEPS_TESTING}" = "1" ]; then \
        nix-env -iP python3-3.8.2 ; \
        nix-env --set-flag priority 6 python3-3.8.2 ; \
        nix-env -iP python3-3.6.10 ; \
        nix-env --set-flag priority 7 python3-3.6.10 ; \
        nix-env -iP python3-3.5.9 ; \
        nix-env --set-flag priority 8 python3-3.5.9 ; \
    fi

# download monero tests binary

RUN if [ "${FULLDEPS_TESTING}" = "1" ]; then \
        TREZOR_MONERO_TESTS_SHA256SUM=1e5dfdb07de4ea46088f4a5bdb0d51f040fe479019efae30f76427eee6edb3f7 ; \
        TREZOR_MONERO_TESTS_URL="https://github.com/ph4r05/monero/releases/download/v0.15.0.0-tests-u18.04-03/trezor_tests" ; \
        wget --no-verbose "${TREZOR_MONERO_TESTS_URL}" -O "${TREZOR_MONERO_TESTS_PATH}" ; \
        chmod +x "${TREZOR_MONERO_TESTS_PATH}" ; \
        echo "${TREZOR_MONERO_TESTS_SHA256SUM} ${TREZOR_MONERO_TESTS_PATH}" | sha256sum -c ; \
        nix-shell -p patchelf --run 'patchelf --set-interpreter "$(cat $NIX_CC/nix-support/dynamic-linker)" "${TREZOR_MONERO_TESTS_PATH}"' ; \
    fi
