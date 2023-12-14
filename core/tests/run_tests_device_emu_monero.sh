#!/usr/bin/env bash

: "${FORCE_DOCKER_USE:=0}"

CORE_DIR="$(SHELL_SESSION_FILE='' && cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"

DOCKER_ID=""

# Test termination trap
terminate_test() {
  if [ -n "$DOCKER_ID" ]; then docker kill $DOCKER_ID 2>/dev/null >/dev/null; fi
}

set -e
trap terminate_test EXIT

export TEST_MIN_HF=15  # No need to test hard fork 12 or lower

if [[ "$OSTYPE" != "linux-gnu" && "$OSTYPE" != "darwin"* ]]; then
  echo "Tests with native Monero app is supported only on Linux and OSX at the moment. Your OS: $OSTYPE"
  exit 0
fi

# When updating URL and sha256sum also update the URL in ci/shell.nix.
error=1
: "${TREZOR_MONERO_TESTS_URL:=https://github.com/ph4r05/monero/releases/download/v0.18.3.1-dev-tests-u18.04-01/trezor_tests}"
: "${TREZOR_MONERO_TESTS_SHA256SUM:=d8938679b69f53132ddacea1de4b38b225b06b37b3309aa17911cfbe09b70b4a}"
: "${TREZOR_MONERO_TESTS_PATH:=$CORE_DIR/tests/trezor_monero_tests}"
: "${TREZOR_MONERO_TESTS_LOG:=$CORE_DIR/tests/trezor_monero_tests.log}"
: "${TREZOR_MONERO_TESTS_CHAIN:=$CORE_DIR/tests/trezor_monero_tests.chain}"

if [[ ! -f "$TREZOR_MONERO_TESTS_PATH" ]]; then
  echo "Downloading Trezor monero tests binary ($TREZOR_MONERO_TESTS_SHA256SUM) to ${TREZOR_MONERO_TESTS_PATH}"
  wget -O "$TREZOR_MONERO_TESTS_PATH" "$TREZOR_MONERO_TESTS_URL" \
    && chmod +x "$TREZOR_MONERO_TESTS_PATH" \
    && echo "${TREZOR_MONERO_TESTS_SHA256SUM}  ${TREZOR_MONERO_TESTS_PATH}" | shasum -a 256 -c
else
  echo "Trezor monero binary already present at $TREZOR_MONERO_TESTS_PATH - not downloading again."
fi

echo "Running tests"
TIME_TESTS_START=$SECONDS
if [[ "$OSTYPE" == "linux-gnu" && "$FORCE_DOCKER_USE" != 1 ]]; then
  echo "Note: use --heavy-tests with real device (and TREZOR_PATH) env var"
  TEST_MAX_HF=15 TEST_MIN_HF=15 "$TREZOR_MONERO_TESTS_PATH" --fix-chain --chain-path=$TREZOR_MONERO_TESTS_CHAIN $@ 2>&1 > "$TREZOR_MONERO_TESTS_LOG"
  error=$?

elif [[ "$OSTYPE" == "darwin"* || "$FORCE_DOCKER_USE" == 1 ]]; then
  DOCKER_ID=$(docker run -idt --mount type=bind,src="$CORE_DIR",dst="$CORE_DIR" -w "$CORE_DIR" --network=host ubuntu:18.04)
  docker exec $DOCKER_ID apt-get update -qq 2>/dev/null >/dev/null
  docker exec $DOCKER_ID apt-get install --no-install-recommends --no-upgrade -qq net-tools socat 2>/dev/null >/dev/null
  docker exec -d $DOCKER_ID socat UDP-LISTEN:21324,reuseaddr,reuseport,fork UDP4-SENDTO:host.docker.internal:21324
  docker exec -d $DOCKER_ID socat UDP-LISTEN:21325,reuseaddr,reuseport,fork UDP4-SENDTO:host.docker.internal:21325
  docker exec -e TEST_MAX_HF=15 -e TEST_MIN_HF=15 $DOCKER_ID "$TREZOR_MONERO_TESTS_PATH" 2>&1 > "$TREZOR_MONERO_TESTS_LOG"
  error=$?

else
  echo "Unsupported OS: $OSTYPE"
  exit 1
fi


TIME_TESTS_ELAPSED=$((SECONDS-TIME_TESTS_START))

if ((error != 0)); then
  RESULT=FAIL
else
  RESULT=PASS
fi

echo "[$RESULT] Monero test in $TIME_TESTS_ELAPSED sec. "
cat "$TREZOR_MONERO_TESTS_LOG" | grep -v DEBUG | egrep '#TEST#|tests.core\b' | tail -n 50
exit $error
