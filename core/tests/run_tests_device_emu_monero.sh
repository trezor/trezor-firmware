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

error=1
: "${TREZOR_MONERO_TESTS_PATH:=$CORE_DIR/tests/trezor_monero_tests}"
: "${TREZOR_MONERO_TESTS_LOG:=$CORE_DIR/tests/trezor_monero_tests.log}"
: "${TREZOR_MONERO_TESTS_CHAIN:=$CORE_DIR/tests/trezor_monero_tests.chain}"

# The binary is built from ph4r05/monero and the patches in tests/monero/,
# see docs/tests/monero-tests.md.
if [[ ! -f "$TREZOR_MONERO_TESTS_PATH" ]]; then
  echo "Trezor monero tests binary not found at $TREZOR_MONERO_TESTS_PATH."
  echo "Build it with core/tests/monero/build.sh DIR (needs docker) and set TREZOR_MONERO_TESTS_PATH=DIR/trezor_tests."
  exit 1
fi
if [[ -f "$TREZOR_MONERO_TESTS_PATH.sha256" ]]; then
  (cd "$(dirname "$TREZOR_MONERO_TESTS_PATH")" && sha256sum -c "$(basename "$TREZOR_MONERO_TESTS_PATH").sha256")
fi
chmod +x "$TREZOR_MONERO_TESTS_PATH"

# The binary uses the system dynamic loader. Where it is missing (NixOS), run a copy
# patched to use the loader of the running bash (nix-provided in nix-shell).
if command -v patchelf >/dev/null && [[ ! -e "$(patchelf --print-interpreter "$TREZOR_MONERO_TESTS_PATH")" ]]; then
  patched="$CORE_DIR/tests/trezor_monero_tests.patched"
  cp "$TREZOR_MONERO_TESTS_PATH" "$patched"
  chmod u+w "$patched"
  patchelf --set-interpreter "$(patchelf --print-interpreter "$(readlink -f "$(command -v bash)")")" "$patched"
  TREZOR_MONERO_TESTS_PATH="$patched"
fi

echo "Running tests"
TIME_TESTS_START=$SECONDS
TEST_ARGS=("$@")
if [[ "$OSTYPE" == "linux-gnu" && "$FORCE_DOCKER_USE" != 1 ]]; then
  echo "Note: use --heavy-tests with real device (and TREZOR_PATH) env var"
  run_tests_once() {
    TEST_MAX_HF=15 TEST_MIN_HF=15 "$TREZOR_MONERO_TESTS_PATH" --fix-chain --chain-path=$TREZOR_MONERO_TESTS_CHAIN "${TEST_ARGS[@]}" 2>&1 > "$1"
  }

elif [[ "$OSTYPE" == "darwin"* || "$FORCE_DOCKER_USE" == 1 ]]; then
  DOCKER_ID=$(docker run -idt --mount type=bind,src="$CORE_DIR",dst="$CORE_DIR" -w "$CORE_DIR" --network=host ubuntu:18.04)
  docker exec $DOCKER_ID apt-get update -qq 2>/dev/null >/dev/null
  docker exec $DOCKER_ID apt-get install --no-install-recommends --no-upgrade -qq net-tools socat 2>/dev/null >/dev/null
  docker exec -d $DOCKER_ID socat UDP-LISTEN:21324,reuseaddr,reuseport,fork UDP4-SENDTO:host.docker.internal:21324
  docker exec -d $DOCKER_ID socat UDP-LISTEN:21325,reuseaddr,reuseport,fork UDP4-SENDTO:host.docker.internal:21325
  run_tests_once() {
    docker exec -e TEST_MAX_HF=15 -e TEST_MIN_HF=15 $DOCKER_ID "$TREZOR_MONERO_TESTS_PATH" 2>&1 > "$1"
  }

else
  echo "Unsupported OS: $OSTYPE"
  exit 1
fi

# Some tests are occasionally flaky (e.g. decoy selection in wallet_api_tests), so retry
# a failing run. All attempts are kept in $TREZOR_MONERO_TESTS_LOG.
: "${TREZOR_MONERO_TESTS_ATTEMPTS:=3}"
: > "$TREZOR_MONERO_TESTS_LOG"
for ((attempt = 1; attempt <= TREZOR_MONERO_TESTS_ATTEMPTS; attempt++)); do
  attempt_log="$TREZOR_MONERO_TESTS_LOG.attempt"
  # With set -e a failing test run would exit before the summary below.
  error=0
  run_tests_once "$attempt_log" || error=$?
  { echo "===== attempt $attempt/$TREZOR_MONERO_TESTS_ATTEMPTS, exit code $error ====="; cat "$attempt_log"; echo; } >> "$TREZOR_MONERO_TESTS_LOG"
  if ((error == 0)); then
    break
  fi
  echo "[FAIL] Monero test attempt $attempt/$TREZOR_MONERO_TESTS_ATTEMPTS:"
  grep -v DEBUG "$attempt_log" | grep -E '#TEST# Failed|Exception at' | tail -n 50
done


TIME_TESTS_ELAPSED=$((SECONDS-TIME_TESTS_START))

if ((error != 0)); then
  RESULT="FAIL"
elif ((attempt > 1)); then
  RESULT="PASS (attempt $attempt/$TREZOR_MONERO_TESTS_ATTEMPTS, earlier attempts failed)"
else
  RESULT=PASS
fi

echo "[$RESULT] Monero test in $TIME_TESTS_ELAPSED sec. "
if ((error == 0 && attempt > 1)) && [[ -n "${GITHUB_ACTIONS:-}" ]]; then
  echo "::warning title=Flaky Monero tests::Passed on attempt $attempt/$TREZOR_MONERO_TESTS_ATTEMPTS, see the core-test-monero-* artifact for the failed attempts"
fi
cat "$attempt_log" | grep -v DEBUG | egrep '#TEST#|tests.core\b' | tail -n 50
rm -f "$attempt_log"
exit $error
