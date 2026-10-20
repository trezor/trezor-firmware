# Threat model

This is `trezor/trezor-firmware`: the source and build for Trezor
hardware wallets. A Trezor is a dedicated signing device. The seed,
PIN, passphrase, and private keys live on the device and must not
leave it. The host (Trezor Suite, Trezor Connect, any USB/BLE client)
proposes transactions and firmware; it is untrusted. The user must
see the true details on the device screen and confirm there
(WYSIWYS) before anything is signed or a secret is used, except for
the operations listed under "Silent by design" below.

This repo is that on-device firmware, not Suite or Connect. **Trezor
Core** (`core/`) is the current stack (MicroPython + Rust + C) on
STM32: Model T (`T2T1`), Safe 3 (`T2B1` / `T3B1`), Safe 5 (`T3T1`),
Safe 7 (`T3W1`). `legacy/` is Trezor One and is **out of scope** for
this scan. Shared C libraries (`crypto/`, `storage/`), coin/protobuf
defs (`common/`), and the host Python client used in tests
(`python/`) live here too.

Top-level dirs:

- `core/` — Trezor Core (MicroPython + Rust + C)
- `legacy/` — Trezor One (C), out of scope
- `crypto/` — C crypto library
- `storage/` — NORCOW (C)
- `python/` — host client (trezorlib + `trezorctl`), not the device
- `common/` — coin defs + protobuf
- `rust/` — standalone Rust crates
- `tests/` — integration suite
- `tools/`, `vendor/` (submodules)

How to build and run (`nix-shell`, `uv`, `xtask`, `emu.py`, tests):
`/src/AGENTS.md`. That file is the compact guide for assistants;
verify commands against the Makefiles if in doubt. Architecture:
`/src/docs/core/embed-arch/embed-arch.md`.

A finding that breaks the guarantee above is in scope even if the C
crypto is correct.

Use test mnemonics only; record the access path, not the secret.
Past issues and bounty ranking: https://trezor.io/security.

The checkout is `/src`. Submodules, the nix-shell toolchain, `.venv`
and a T3T1 unix emulator (`-p test-live`) are already set up, and
every bash shell loads the environment from
`/etc/trezor-firmware-env.sh`. There is no network: skip the
`nix-shell` / `uv sync` / `git submodule` setup steps in
`AGENTS.md`. Default binary:
`/src/core/build/artifacts/latest/firmware-emu`. Follow
`/src/AGENTS.md` to start it. This image is T3T1, not T3W1
(no Tropic). The unix port does not model STM32 MPU / kernel /
secmon — argue those from source.

## What this project does and where untrusted input enters

Untrusted input arrives from the host (Suite, Connect, any USB/BLE
client):

- USB / BLE: Codec v1 protobuf or THP (pairing, credentials, sessions)
  in `core/src/trezor/wire/`, `core/src/apps/thp/`, `common/protob/`
- Raw USB packets (`core/embed/io/usb/`) and their reassembly into
  Codec v1 / THP frames (`core/src/trezor/wire/`,
  `core/embed/rust/src/thp/`), decoded by the Rust protobuf decoder
  (`core/embed/rust/src/protobuf/`)
- BLE (Safe 7, `T3W1`): the radio is handled by a separate nRF chip.
  Its firmware (`nordic/`) is out of scope. The STM32 talks to it over
  UART/SPI (`core/embed/io/nrf/`, `core/embed/io/ble/`), carrying BLE
  data plus pairing requests, bond lists and the MAC address. Treat
  everything from the nRF as untrusted: a radio attacker may control it.
- Bootloader: firmware-update messages decoded with nanopb
  (`core/embed/projects/bootloader/`)
- Application messages after the transport (`workflow_handlers.py` →
  coin apps, management, WebAuthn, extapp)
- Chunked transactions, firmware images, pairing (QR / NFC / code)
- Storage blobs and PIN attempts (`storage/`)
- Crypto inputs (keys, signatures, paths, SLIP-39) in `crypto/`
- Third-party app payloads in the application arena

On STM32U5 (Safe 3 `T3B1`, Safe 5, Safe 7) coreapp is unprivileged;
kernel and secmon sit under it (`docs/core/embed-arch/embed-arch.md`).
Model T and Safe 3 `T2B1` are STM32F4: no TrustZone, no secmon; the
kernel takes that role.

Priority models: Safe 5 (`T3T1`) and Safe 7 (`T3W1`); Safe 3 for
button-UI confirmation; Model T (`T2T1`) when the bug is Core-wide.

## Components that matter most / least

Most important:

- **Seed and secrets** — generate, BIP-39 / SLIP-39, wipe, PIN, passphrase
  (`core/src/apps/management/`, `storage/`, `core/embed/sec/rng/`). Host
  entropy must not dominate RNG.
- **Confirmation (WYSIWYS)** — shown == signed. All of `core/src/apps/`
  (bitcoin, ethereum, solana, cardano, zcash, monero, …). Layouts in
  `core/embed/rust` and `core/src/trezor/ui/layouts` when they decide
  what is displayed. Start at `core/src/apps/workflow_handlers.py`.
- **Auth / device state** — PIN, wipe code, autolock, THP pairing,
  firmware-update confirm on device.
- **Host → Core** — malformed protobuf, USB, THP.
- **`crypto/`** — memory safety and correctness of primitives Core calls.
- **Modularization** — kernel, secmon, MPU, syscalls/smcalls,
  IPC, 3rd-party app loader. A sandboxed app must not read secrets, skip
  confirmation, or run unsigned code:
  - `core/embed/projects/kernel/`, `core/embed/projects/secmon/`
  - `core/embed/sys/mpu/` (`stm32u5/mpu.c`), `syscall/`, `smcall/`, `ipc/`
    (`syscall_verifiers.c`, `smcall_verifiers.c`)
  - `core/embed/io/app_arena/`, `core/embed/api/`
  - `core/src/apps/extapp/`, `common/protob/messages-extapp.proto`

- **Build / release integrity** — anything that decides what ends up
  in a signed production image: production vs debug features in
  `core/embed/xtask/` and the Makefiles (debuglink, dev keys, insecure
  PRNG or storage test mode leaking into `--production`), header and
  hash tools (`core/tools/trezor_core_tools/`, `headertool*.py`,
  `bootloader_hashes.py`), firmware fingerprints
  (`python/tools/*-fingerprint.py`, `build-docker.sh`), code
  generated from `common/defs/` and `common/protob/`. Argue these
  from source; do not run release builds here.

In scope, lower: `python/` parsers; UI copy except confirmation.

Hunt classes: weak/truncated seed RNG; change mis-labelled as ours;
testnet/mainnet mixup; payload swapped after confirm; MPU overlap;
forged app header/hash chain.

### Silent by design

These use the seed or a device secret without a per-operation prompt
(device unlocked, session open). They are intended:

- `show_display=false` getters of public data: `GetPublicKey`,
  `GetAddress` and the per-coin variants, including the SLIP-24
  address MAC. Bitcoin `GetPublicKey` (any curve),
  `EthereumGetPublicKey` and `CipherKeyValue` accept any path, even
  with Strict safety checks.
- `GetOwnershipId`; `GetOwnershipProof` with `user_confirmation=false`.
- `CipherKeyValue` with `ask_on_encrypt` / `ask_on_decrypt` false (the
  ask flags are part of the key derivation).
- After `AuthorizeCoinJoin`: `DoPreauthorized` → `SignTx` /
  `GetOwnershipProof` within the authorized path, coin, fees, rounds.
- `UnlockPath` with a valid MAC (SLIP-25 paths).
- `MoneroLiveRefresh` after the first confirmation in a session.
- Evolu `GetNode` / `SignRegistrationRequest` with a valid proof of
  delegated identity.
- THP: a new session with an empty host passphrase; re-issuing a
  non-autoconnect pairing credential.
- FIDO: U2F check-only; CTAP2 `GetAssertion` with up=false/uv=false
  (no real signature).

It is a finding if one of these returns more than its documented
output (a private key, a real signature where there should be none),
skips its guard (authorization limits, MAC, ask flags, delegated
identity proof), or if any other operation signs or uses a secret
without confirmation.

## How to exercise it

Commands: `/src/AGENTS.md` (and the Makefiles). Do not invent a
second procedure here.

Use only the prebuilt tools below; they are known to work in this
image. Do not build other variants (ASAN emulator via `--asan` /
`-p dev`, other models, frozen or production builds). If a tool
fails in this image, do not debug or fix the environment: fall back
to source review. (A failure that points at a real bug in how
production firmware is built is a finding; see "Build / release
integrity".)

- **Emulator / device tests:** `emu.py` as in `AGENTS.md`. This
  image's `latest` firmware-emu is **T3T1**. Do not start T3W1
  (Tropic). Do not run the UI screenshot suite (`--ui=test`,
  `test_emu_ui`).
- **`core/src/` and `core/embed/`:** source-review for kernel,
  MPU, secmon, syscalls. Map messages through
  `core/src/apps/workflow_handlers.py`.
- **`crypto/`:** prebuilt with ASAN + UBSAN (`ASAN_OPTIONS` is set in
  the environment). Run `CK_TIMEOUT_MULTIPLIER=20 /src/crypto/tests/test_check`
  and `cd /src/crypto && ITERS=10 pytest tests`.
- **Core unit tests:** `make -C /src/core test`, or one file with
  `TESTOPTS=<file>` (files in `core/tests/`).
- **`storage/`:** `make -C /src/storage/tests tests` (prebuilt)
- This image is x86-64; 32-bit-only MCU bugs: argue from source and
  rate them by impact (not reproducing them here limits the evidence,
  not the severity).

## How you rate severity

Calibrate to https://trezor.io/security. When a finding fits several
tiers, use the highest one its impact supports.

- **Critical** — seed/key extraction or injection; PIN/passphrase bypass;
  confirmation bypass (signed ≠ shown); unauthenticated firmware on a
  locked production device; sandbox escape or loader bypass that yields
  secrets or unsigned code on a locked production Safe.
- **High** — host-reachable memory corruption without a full exploit;
  bad signature/MAC/THP verify; path/policy bypass; attestation a swapped
  SE can pass.
- **Medium** — USB/BLE DoS; non-secret leak; remotely useful PIN/THP
  timing; coin-logic that does not by itself move funds. A reconnect-only
  crash is lower than a signing oracle.
- **Low** — trezorlib-only crash; emulator-only issues that do not
  affect hardware.
  (Debuglink / unlocked bootloader / non-production-only issues are
  out of scope, see below.)

For confirmation bugs, compare displayed fields vs signed preimage. For
seed bugs, test wallets only — record the path, not the secret.

## Anything to leave alone

- The user approving a transaction whose details are decoded and shown
  correctly: we don't prevent user mistakes. Also content hidden in
  data the device presents as raw / blind-signed (e.g. Ethereum
  calldata, Solana blind signing). Display that is technically
  correct but misleading (truncation, wrong units or labels,
  ambiguous rendering, falling back to blind signing without saying
  so) **is** a finding.
- `legacy/` (Trezor One, `T1B1`): do not scan or report it. Shared
  code (`crypto/`, `storage/`) stays in scope as Core uses it; a bug
  reachable only through `legacy/` is out of scope.
- `tests/`, `ci/`, `docs/`, `apps/debug/`, `apps/benchmark/`, debuglink,
  non-production builds, discovery boards
- Dev / test conveniences that never reach a production image
  (`emu.py`, test harnesses, sanitizer setup, this scanner image):
  do not fix them or report problems in them. Build steps that shape
  production firmware are in scope (see above).
- `vendor/` except how we feed it untrusted bytes (nanopb in the
  bootloader)
- `nordic/` (nRF BLE firmware); its messages to the STM32 stay in scope
- Codec v1 being unencrypted on old models (by design)
- Documented unlocked bootloader running unsigned firmware
- Weak algorithms merely being implemented; `crypto/` API misuse that
  production callers never do

## How reports should look

Findings go privately to `security@satoshilabs.com` only. Do not put
suspected vulnerabilities, reproducer details, private review history,
or unreviewed findings into public issues or PRs. Disclosure decisions
belong to the project's security contacts.

Each report should include:

- commit (`git -C /src rev-parse HEAD`), model, production vs debug
- attacker (USB host, unpaired BLE, sandboxed app, …) and consequence
- the smallest bounded reproducer, actual output, expected result,
  and relevant evidence limits

Patches: small, existing style; do not expand debuglink or weaken
production checks.
