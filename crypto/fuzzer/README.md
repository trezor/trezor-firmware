# trezor-crypto fuzzing
Selected functions can be fuzzed via specific libFuzzer harnesses for increased test coverage and issue detection.

Note: the following commands are relative to the trezor-crypto main directory.

## Build

A modern C compiler with built-in libFuzzer support is required. The build process will use `clang` by default.
Set the `CC=` environment variable if you want to use a special compiler variant.

```bash
make clean
FUZZER=1 make fuzzer
```

### Sanitizers
Recommended: ASAN / UBSAN / MSAN flags for error detection can be specified via the special `SANFLAGS`.

Examples:

  * `SANFLAGS="-fsanitize=address,undefined"`
  * `SANFLAGS="-fsanitize=memory"`

### Optimizations

Override `OPTFLAGS` to test the library at different optimization levels or simplify the debugging of detected issues.

Example:

  * `OPTFLAGS="-O0 -ggdb3"`

## Operation

See the [libFuzzer documentation](https://llvm.org/docs/LibFuzzer.html#options) for valid options and usage. Detailed fuzzer usage and relevant considerations are out of scope of this document.

**Warning**: fuzzing is resource-intensive and can have a negative impact on your system stability.

Basic fuzzer call:
```bash
./fuzzer/fuzzer
```

Here is a more sophisticated multithreading example with a persistent input corpus and other optimizations:
```bash
mkdir fuzzer/fuzzer_corpus
./fuzzer/fuzzer -max_len=2048 -use_value_profile=1 -jobs=16 -timeout=1 -reload=5 -print_pcs=1 -print_funcs=42  fuzzer/fuzzer_corpus
```

Hint: for more permanent setups, consider invoking the fuzzer from outside of the source directory to avoid cluttering it with logfiles and crash inputs.

## Automated fuzzer dictionary generation

[Dictionaries](https://llvm.org/docs/LibFuzzer.html#dictionaries) are a useful mechanism to augment the capabilities of the fuzzer. Specify them via the `-dict=` flag.

### Collect interesting strings from the unit tests
``` bash
grep -r -P -o -h  "\"\w+\"" tests | sort  | uniq > fuzzer_crypto_tests_strings_dictionary1.txt
```

## Evaluate source coverage

  1. build the fuzzer binary with `CFLAGS="-fprofile-instr-generate -fcoverage-mapping"`
  1. run with suitable `-runs=` or `-max_total_time=` limits
  1. convert the recorded data `llvm-profdata merge -output=default.profdata -instr default.profraw`
  1. render the data `llvm-cov show fuzzer/fuzzer -instr-profile=default.profdata -format=html -output-dir=coverage-report`
  1. analyze report at `coverage-report/index.html`
  1. (optional) remove artifacts with `rm default.profraw default.profdata && rm -r coverage-report`
