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

The app calls one layout and answers with how it ended (`UiResult`). A
review, a danger and a verify layout answer `Confirmed` for a yes and
`Cancelled` for a refusal — for the verify layouts a mismatch is a `Cancelled`
too; a `details` answers `ShowDetails` when the person wants them,
`Confirmed` when they accept without, and `Cancelled` when they refuse. `Done`
and a progress ask nothing, so their answer says nothing about a decision. A
request the app refuses, such as two `data` fields, a sixth extra or a
streamed `data` field inside an extra, comes back as a `Failure`; so does a
source whose read fails, with that source's own error. One Core cannot draw ends
the app, as every app's would.
The host plays the app's part here, so it picks every parameter, the step name
included (`--step`, defaulting to the layout's name).

| Request | Layout |
| ------- | ------ |
| `Review` | `modui::review(step, title, &fields).confirm()` |
| `Review` (final) | the same, with `.confirm_final()` |
| `Extra` | `Extra::new(label, &fields)`, in a review's `.extras(&[...])` |
| `Danger` | `modui::review(step, title, &fields).confirm_danger()` |
| `Details` | `modui::details(step, title, &fields)` |
| `VerifyAddress` | `modui::verify_address(step, address, account, path)` |
| `VerifyPubkey` | `modui::verify_pubkey(step, pubkey, account, path)` |
| `Done` | `modui::done(step, text)` |
| `ShowProgress` | `modui::progress(label, total, work)` |
| `StreamData` | a review with a `data_source` field, then a final review of its hash |
| `ProgressLabel` | `Progress::label(text)`, while a progress runs |

`account` and `path` are optional in the verify layouts. A review's extras
travel with its request, as one `.extras(&[Extra::new(label, &fields), ...])`
call, and an extra with no facts is not offered. A progress stays on the device
while the app works: the app asks the host for each step, and the host answers
with the next step, a new label, or the end. A `StreamData` request has the app
generate `length` bytes, hash them as it hands them out, and show the hash and
the number of reads in a final review; `fail_at` makes the k-th read fail, and
the host then sees the app's own error rather than a cancel.

`tests/test_modui.py` runs with the device tests above. Core draws an app's
screens, so debuglink reads and drives them like any other: each layout is
confirmed and cancelled, its extras menu opened and left, and every asking
layout must send exactly one ButtonRequest, named `testapp.trezor.io/<step>`, however
long the menu is open (a paged layout sends one per page).
`tests/test_showcase.py` drives every showcase the same way.

### Showcase

`testappctl showcase <name>` runs one example from the reference as it
stands, so each layout can be seen with realistic facts:

| Name | Shows |
| ---- | ----- |
| `send` | two reviews, with an "Account info" extra |
| `delegate` | one review with address, amount and text facts |
| `claim-owner` | a review with a warning beside an address |
| `unknown-contract` | a `danger` for an unknown contract |
| `path-warning` | a `danger` for an unusual path |
| `typed-data` | a `details`, then a review per member |
| `get-address` | a `verify_address` |
| `get-pubkey` | a `verify_pubkey` |
| `contract-data` | a review with a `data` field |
| `consent` | a review with a note only |
| `swap` | a final review with amounts, a caution and five extras |
| `fee-bump` | a final review with a transaction ID and fees, and an extra |
| `sign-message` | a final review with an address and a message |
| `verify-message` | a review, then `done` |
| `signing-progress` | a `progress`, with the label changing per step |

### Run by hand

Build the emulator and the app as above (any model), start the emulator
(`core/emu.py`), then run one layout at a time:

```sh
sdk/apps/testapp/host/testappctl --help
sdk/apps/testapp/host/testappctl showcase send
sdk/apps/testapp/host/testappctl showcase unknown-contract
sdk/apps/testapp/host/testappctl showcase signing-progress
sdk/apps/testapp/host/testappctl stream-data --length 1025
```

`testappctl showcase --help` lists the names. The app is loaded afresh each run,
so a rebuilt app is what runs; `--no-reload` skips that. Like `trezorctl`, it
talks to the device at `TREZOR_PATH` (such as `udp:127.0.0.1:32500` for an
emulator started with `-P 32500`), or to the first one it finds.

### Host library

`host/testapp_host` is the part meant to outlive manual testing; `cli.py` is
only a frontend over it. It loads the app, sends one request and returns the
answer, and `messages` is the module the device tests use too:
`tests/generated/messages.py`, generated from `protob/*.proto` by
`cargo app-tool gen-py` and regenerated whenever a `.proto` is newer, so both
sides of the wire always agree.
