# Tests

## Device tests (run against the emulator)

Start the emulator first (in a separate terminal, from `core/`):
```sh
./emu.py -a        # -a disables animations
```

Then run tests from the repo root:
```sh
pytest tests/device_tests
pytest tests/device_tests -k nem              # filter by name
pytest tests/device_tests -k "nem or stellar"
pytest tests/device_tests -m stellar          # filter by marker
pytest tests/device_tests -v -s              # verbose + print output
```

Or use the Makefile target (starts emulator automatically):
```sh
cd core && make test_emu
cd core && make test_emu TESTOPTS="-k test_sign_tx"
```

Other `test_emu_*` targets: `test_emu_click`, `test_emu_ui`, `test_emu_persistence`, `test_emu_fido2`, `test_emu_monero`.

### Model markers

Tests can be restricted by model using `@pytest.mark.models(...)`:
- `"core"` — all trezor-core models (excludes Trezor One)
- `"legacy"` — Trezor One only
- `"safe3"` — covers T2B1 and T2T1
- `"delizia"` — T3T1 only
- `"eckhart"` — T3W1 only
- or explicit model names: `"t3t1"`, `"t2b1"`, etc.

## Python unit tests (MicroPython, run via emulator binary)

Tests live in `core/tests/` and run through the emulator binary as MicroPython scripts:
```sh
cd core/tests
./run_tests.sh                    # all tests
./run_tests.sh test_apps.bitcoin.signtx.py   # single file
```

## Rust unit tests

```sh
cd core && make test_rust
```

Runs `cargo test` for the Rust crate in `core/embed/rust/` with the appropriate target and feature flags.
