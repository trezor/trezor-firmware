# testapp

A test-only app that exposes the SDK to the host, in two halves:

- **crypto**: every SDK crypto function (`trezor_app_sdk::crypto`), so device
  tests can exercise the crypto API end to end: from the app, through the app
  API, to Core;
- **UI**: every modui layout (`trezor_app_sdk::modui`), so the UI can be
  exercised by hand on every model.

**Never ship it.** It is dev-signed only and must stay out of every release
bundle.

Each wire request names one crypto function or one layout and carries its
parameters one to one (`protob/testapp.proto`).

## Crypto

The app calls the function and answers with its result. An error the function
returns comes back to the host as a `Failure` whose code is the SDK's
`Error::code()`; the app keeps running.

A parameter the function's types can't hold (a digest that isn't 32 bytes, a
sigmask over 255, ...) is refused with `InvalidArgument` before the function is
called.

| Request | Function | Response |
|---|---|---|
| `Hash` | `get_hasher`, fed `chunks` one update at a time | `Digest` |
| `Hmac` | `get_hmac`, fed `chunks` one update at a time | `Digest` |
| `GetXpub` | `get_xpub` | `Xpub` |
| `GetPublicKey` | `get_public_key` | `PublicKey` |
| `EcdsaSignDigest` | `ecdsa_sign_digest` | `Signature` |
| `Ed25519Sign` | `ed25519_sign` | `Signature` |
| `GetAddressMac` | `get_address_mac` | `AddressMac` |
| `CheckAddressMac` | `check_address_mac` | `Bool` |
| `VerifyNonceCache` | `verify_nonce_cache` | `Bool` |
| `EcdsaVerify` | `ecdsa_verify_digest` of the message's SHA-256 digest | `Success` |
| `EcdsaVerifyDigest` | `ecdsa_verify_digest` | `Success` |
| `EcdsaRecoverPubkey` | `ecdsa_recover_pubkey` | `PublicKey` |
| `Ed25519Verify` | `ed25519_verify` | `Success` |
| `CosiVerify` | `cosi_verify` | `Success` |
| `CosiCombinePublicKeys` | `cosi_combine_publickeys` | `PublicKey` |
| `Base58Encode` / `Base58Decode` | `base58_encode` / `base58_decode` | `Base58` / `Data` |
| `Base58CheckEncode` / `Base58CheckDecode` | `base58check_encode` / `base58check_decode` | `Base58` / `Data` |

The manifest allows secp256k1 and testnet BIP-44 paths
(`m/44'/1'/account'/change/address_index/**`), so signing works there and is
refused elsewhere.

### Device tests

`tests/` follows the tron app's layout. Expected values never come from the
device:

- `tests/fixtures/*.json` hold static vectors computed with independent
  implementations: `hashlib`/`hmac`, pycryptodome (Keccak), trezorlib's base58,
  and BIP-32 derivation of the `all all ... all` seed.
- Signatures to verify are made on the host (`ecdsa`, `cryptography`,
  trezorlib's CoSi); signatures the device makes are checked with `ecdsa`.

Build an emulator with app loading and debuglink, build the app, start the
emulator, then run the tests:

```sh
xtask build firmware -e -m T3W1 -p test-live --apps true
cd sdk/apps
cargo app-tool build -p testapp -m t3w1 --lang en -d -e
cargo app-tool device-test -p testapp -m t3w1 -e
```

## UI

The app calls the layout and answers with how it ended (`UiResult`):
`Confirmed` or `Cancelled`, for a confirmation and a notice alike; a progress
answers `Confirmed` once it has run. A request the app refuses, such as a
value with both a hint and a warning, comes back as a `Failure`; one Core
cannot draw ends the app, as every app's would. The host picks every
parameter, including the step name (`br`).

| Request | Layout |
|---|---|
| `ConfirmAction` | `modui::confirm::action` |
| `ConfirmValue` | `modui::confirm::value` |
| `ConfirmData` | `modui::confirm::data` |
| `ConfirmProperties` | `modui::confirm::properties` |
| `ConfirmSummary` | `modui::confirm::summary` |
| `ShowNotice` | `modui::notice::show` |
| `ShowProgress` | `modui::progress::run_with`, paced by the host (below) |

`tests/test_modui.py` runs with the device tests above. Core draws an app's
screens, so debuglink reads and drives them like any other: each layout is
confirmed and cancelled, its extras menu opened and left, and every layout
must send exactly one ButtonRequest, named by `br`, however long the menu is
open (a paged layout sends one per page). Where a model draws less than a
layout asks for, the test is reported as an expected failure (`GAPS`).

### Run by hand

Build the emulator and the app as above (any model), start the emulator
(`core/emu.py`), then drive one layout at a time:

```sh
sdk/apps/testapp/host/testappctl --help
sdk/apps/testapp/host/testappctl action --final \
    --extra "Account info" "Account=Tron #1" "Path=m/44'/195'/0'"
sdk/apps/testapp/host/testappctl value --address --footer-warning "Not yours"
sdk/apps/testapp/host/testappctl notice --severity danger
sdk/apps/testapp/host/testappctl progress --total 20 --steps 20
```

Every subcommand has sensible defaults, so `testappctl action` alone works.
The app is loaded afresh each run, so a rebuilt app is what runs;
`--no-reload` skips that.

### Host library

`host/testapp_host` is the part meant to outlive manual testing; `cli.py` is
only a frontend over it.

```python
from testapp_host import TestApp, connect, messages as m

app = TestApp.load(connect())
result = app.call(m.ConfirmAction(title="Send", action="Really?", br="t/1"))
assert result.reply == m.Reply.Confirmed
```

A progress stays on the device for as long as a `with` block runs, and ends
however the block ends. The app asks the host for each step (`ProgressTick`),
the host answers `ProgressStep` or, on leaving the block, `ProgressEnd`:

```python
with app.progress("Working...", total=len(chunks)) as p:
    for chunk in chunks:
        process(chunk)
        p.step()
```

`messages` is the module the device tests use too: `tests/generated/messages.py`,
generated from `protob/*.proto` by `cargo app-tool gen-py` and regenerated
whenever a `.proto` is newer, so both sides of the wire always agree.
