#!/usr/bin/env bash

declare -a results
declare -i passed=0 failed=0 skipped=0 exit_code=0
declare COLOR_GREEN='\e[32m' COLOR_RED='\e[91m' COLOR_YELLOW='\e[33m' COLOR_RESET='\e[39m'
MICROPYTHON="${MICROPYTHON:-../build/unix/trezor-emu-core -X heapsize=2M}"
export SDL_VIDEODRIVER=dummy

print_summary() {
    echo
    echo 'Summary:'
    echo '-------------------'
    printf '%b\n' "${results[@]}"
    if [ $exit_code == 0 ]; then
        echo -e "${COLOR_GREEN}PASSED:${COLOR_RESET} $passed/$num_of_tests tests OK!"
        echo -e "${COLOR_YELLOW}SKIPPED:${COLOR_RESET} $skipped/$num_of_tests tests skipped!"
    else
        echo -e "${COLOR_RED}FAILED:${COLOR_RESET} $failed/$num_of_tests tests failed!"
    fi
}

trap 'print_summary; echo -e "${COLOR_RED}Interrupted by user!${COLOR_RESET}"; exit 1' SIGINT

cd $(dirname $0)

[ -z "$*" ] && tests=(test_*.py) || tests=($*)

declare -i num_of_tests=${#tests[@]}

export MICROPYPATH=.:../src  # for tests' imports to work as expected

for test_case in "${tests[@]}"; do
    echo

    output=$($MICROPYTHON "$test_case")
    echo "$output"

    # go through all lines that start with "RESULT:" and take the last one
    result_line=$(grep -E '^RESULT:' <<< "$output" | tail -n1)

    if [ "$result_line" = "RESULT:OK" ]; then
        results+=("${COLOR_GREEN}OK:${COLOR_RESET} $test_case")
        ((passed++))
    elif [ "$result_line" = "RESULT:FAILED" ]; then
        results+=("${COLOR_RED}FAIL:${COLOR_RESET} $test_case")
        ((failed++))
        exit_code=1
    else
        results+=("${COLOR_YELLOW}SKIPPED:${COLOR_RESET} $test_case")
        ((skipped++))
    fi
done

print_summary
exit $exit_code
