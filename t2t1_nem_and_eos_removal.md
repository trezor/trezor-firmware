# EOS + NEM removal — flash savings report

**Build config:** `xtask build firmware -m t2t1 --pyopt false --debug-link` (universal firmware)

## Results

| Stage | FLASH | FLASH2 |
|---|---|---|
| Baseline | 761.5 KB (99.16%) | 789.8 KB (88.15%) |
| 1. Frozen Python apps (`apps/eos`, `apps/nem`, enums, qstrs) | **737.5 KB** (−24.0 KB) | 787.9 KB (−1.9 KB) |
| 2. Translation strings (87 keys × 6 languages, Rust string table) | 737.5 KB | 786.1 KB (−1.8 KB) |
| 3. Protobuf messages (2 proto files, wire blobs, MessageType/Capability) | 737.5 KB | 784.7 KB (−1.4 KB) |
| 4. C crypto (`crypto/nem.c`, `trezorcrypto.nem` module, `HDNode.nem_*`) | 737.5 KB (96.03%) | **778.8 KB** (86.91%) |

**Total: −24.0 KB FLASH, −11.0 KB FLASH2 → ~35 KB combined.** The frozen Python apps dominate; everything else (translations, proto blobs, C crypto) is surprisingly small because most of it lives in FLASH2.

## What was removed

- `core/src/apps/eos/`, `core/src/apps/nem/` — apps + NEM mosaics template
- Handler registrations in `core/src/apps/workflow_handlers.py:187` and `Capability.NEM/EOS` advertisement in `core/src/apps/base.py` (the `T2T1`-only gate)
- `eos`/`nem` features: `core/embed/models/T2T1/model.toml`, `project.toml` (firmware + unix), both `Cargo.toml`s, `build.rs` freeze blocks
- `common/protob/messages-{eos,nem}.proto`, `Capability_EOS/NEM` + `MessageType` entries (reserved, Lisk-style) → regenerated `messages.py`, enums, trezorlib + trezor-client protos
- 87 `eos__*`/`nem__*` keys from all 6 `core/translations/*.json` → regenerated `translated_string.rs`, blobs, qstr tables
- C: `modtrezorcrypto-nem.h`, `nem.h` include + `HDNode.nem_address/nem_encrypt` in `modtrezorcrypto-bip32.h`, `nem.c` from `core/embed/crypto/build.rs`, `USE_NEM/USE_EOS` defines
- Client/tests: `trezorlib/{eos,nem}.py` + CLI modules, device tests, core unit tests, regenerated mocks

**Kept intentionally:** `crypto/nem.c`/`nem.h` source files and `common/defs/nem/` (used by legacy/Trezor One firmware); `tests/ui_tests/fixtures.json` per your instruction.

## Verification

- Both firmware and emulator build; signature valid
- Emulator boots, `GetFeatures` works, capabilities no longer list NEM/EOS
- `pytest tests/device_tests/bitcoin/test_signtx_segwit.py` — 7 passed
- `make protobuf_check`, `make mocks_check`, `make -C core templates_check`, `make -C core translations_check` all pass

Nothing is committed — all changes are in the working tree for inspection.
