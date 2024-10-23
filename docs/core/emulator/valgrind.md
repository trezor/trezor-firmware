# Profiling emulator with Valgrind

Sometimes it can be helpful to know which parts of your code take most of the CPU time.
[Callgrind](https://valgrind.org/docs/manual/cl-manual.html) tool from the [Valgrind](https://valgrind.org/)
instrumentation framework can generate profiling data for a run of Trezor emulator. These can then be visualized
with [KCachegrind](https://kcachegrind.github.io/).

Bear in mind that profiling the emulator is of very limited usefulness due to:
* different CPU architecture,
* different drivers,
* & other differences from actual hardware.
Still it might be a way to get *some* insight without a [hardware debugger](../systemview/index.md)
and a development board.

## Build

```
make build_unix_frozen TREZOR_EMULATOR_DEBUGGABLE=1 ADDRESS_SANITIZER=0
```

With `PYOPT=0` most of the execution time is spent formatting and writing logs so it is recommended to use `PYOPT=1`
(and lose DebugLink) or get rid of logging manually.

## Run

Record profiling data on some device tests:
```
./emu.py -a --debugger --valgrind -c 'sleep 10; pytest ../../tests/device_tests/ -v --other-pytest-args...'
```

Open profiling data in KCachegrind (file suffix is different for each emulator process):
```
kcachegrind src/callgrind.out.$PID
```
