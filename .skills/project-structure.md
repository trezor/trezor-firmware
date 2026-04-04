# Project Structure — trezor-firmware

- `core/` — main firmware (MicroPython + Rust + C)
  - `core/src/apps/` — per-coin/protocol handlers (bitcoin, ethereum, cardano, …)
  - `core/src/trezor/` — core Python package: wire protocol, UI framework, crypto helpers
  - `core/embed/rust/src/ui/` — Rust UI components (`trezorui2` module)
  - `core/embed/rust/src/trezorhal/` — hardware abstraction layer
  - `core/embed/` — bootloader, drivers, MicroPython C modules
- `crypto/` — stand-alone C crypto library (shared by core and legacy)
- `legacy/` — Trezor One firmware
- `common/protob/` — protobuf definitions for the wire protocol
- `common/defs/` — JSON coin definitions
- `python/src/trezorlib/` — host-side Python client library and `trezorctl`
- `storage/` — NORCOW storage implementation
- `tests/` — pytest suite: `device_tests/`, `click_tests/`, `ui_tests/`, `upgrade_tests/`
- `docs/` — documentation (mirrors docs.trezor.io)
- `vendor/` — git submodules

## Generated files — do not edit by hand

`core/src/trezor/messages.py`, `python/src/trezorlib/messages.py`, and Rust protobuf code are generated from `common/protob/*.proto`. Regenerate with `make gen` after changing `.proto` files.
