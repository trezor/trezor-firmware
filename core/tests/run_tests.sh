#!/usr/bin/env bash

declare -a results
declare -i passed=0 failed=0 exit_code=0
declare COLOR_GREEN='\e[32m' COLOR_RED='\e[91m' COLOR_RESET='\e[39m'
MICROPYTHON="${MICROPYTHON:-../build/unix/trezor-emu-core -X heapsize=2M}"

print_summary() {
    echo
    echo 'Summary:'
    echo '-------------------'
    printf '%b\n' "${results[@]}"
    if [ $exit_code == 0 ]; then
        echo -e "${COLOR_GREEN}PASSED:${COLOR_RESET} $passed/$num_of_tests tests OK!"
    else
        echo -e "${COLOR_RED}FAILED:${COLOR_RESET} $failed/$num_of_tests tests failed!"
    fi
}

trap 'print_summary; echo -e "${COLOR_RED}Interrupted by user!${COLOR_RESET}"; exit 1' SIGINT

cd $(dirname $0)

[ -z "$*" ] && tests=(test_*.py) || tests=($*)

declare -i num_of_tests=${#tests[@]}

for test_case in ${tests[@]}; do
    echo
    if $MICROPYTHON $test_case; then
        results+=("${COLOR_GREEN}OK:${COLOR_RESET} $test_case")
        ((passed++))
    else
        results+=("${COLOR_RED}FAIL:${COLOR_RESET} $test_case")
        ((failed++))
        exit_code=1
    fi
done

print_summary
exit $exit_code
