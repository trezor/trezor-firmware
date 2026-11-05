# testapp

A test-only app that exposes the SDK to the host, in two halves:

- **crypto**: every SDK crypto function (`trezor_app_sdk::crypto`), so device
  tests can exercise the crypto API end to end: from the app, through the app
  API, to Core;
- **UI**: every modui endpoint (`trezor_app_sdk::modui`), so device tests can
  exercise the UI end to end, and a person can walk it by hand.

**Never ship it.** It is dev-signed only and must stay out of every release
bundle.

Each wire request names one crypto function or one modui endpoint and carries
its parameters one to one (`protob/testapp.proto`).

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

The app calls one endpoint and answers with how it ended (`UiResult`): a yes is
`Confirmed` and a refusal `Cancelled` (for a verification, a mismatch is a
refusal too). Details answer `ShowDetails` when the person picks "Show all".
`Done` and a progress ask nothing, so their answer says nothing about a
decision. A request the SDK refuses, such as two `data` fields in one list,
more extras than the menu has room for, an extra beside a danger, or a streamed
`data` field inside an extra, comes back as a `Failure`; so does a source whose
read fails, with that source's own error. The host plays the app's part here,
so it picks every parameter, the step name included (`--step`, defaulting to
the endpoint's name).

| Request | Endpoint |
| ------- | -------- |
| `Review` | `modui::review(step, title, &fields).extras(&extras)`, then `answer`: `confirm()`, `confirm_strong()`, `confirm_danger()` or `details()` |
| `Summary` | `modui::summary(step, title)` with each part present, then `confirm_strong()` |
| `VerifyAddress` | `modui::verify_address(step, address, account, path)` |
| `VerifyPubkey` | `modui::verify_pubkey(step, pubkey, account, path)` |
| `Done` | `modui::done(step, text)` |
| `StreamData` | a review of one `Field::data_source` field, then a final review of its hash |
| `ShowProgress` | `modui::progress(label, total, work)`, paced by the host |

A progress stays on the device while the app works: the app asks the host for
each step (`ProgressTick`), and the host answers with `ProgressStep`, a new
label (`ProgressLabel`), a review in the middle of the work (`ProgressReview`),
a second progress inside the first (`ProgressNested`, which core refuses by
stopping the app), or the end (`ProgressEnd`). A `StreamData` request has the
app generate `length` bytes, hash them as it hands them out, and show the hash
and the number of reads in a final review; `fail_at` makes that read fail, and
the host then sees the app's own error rather than a cancel.

`tests/test_modui.py` runs with the device tests above. Core draws an app's
screens, so debuglink reads and drives them like any other: each endpoint is
confirmed and cancelled, its menu opened and left, and every asking endpoint
sends exactly one ButtonRequest, named `testapp.trezor.io/<step>`, however many
pages or chunks it has. `tests/test_showcase.py` runs every example flow the
same way.

### Showcase

The example flows live on the host, in `host/testapp_host/showcases.py`: the app
exposes the endpoints above one to one, and the host picks the facts and the order,
so a flow can react to an answer (typed data, for example, shows the owner review
only when the person asks for the details). `testappctl showcase <name>` runs one,
so each endpoint can be seen with realistic facts:

| Name | Shows |
| ---- | ----- |
| `send` | a review, then a `summary`, then `done` |
| `delegate` | one review, then the final review, then `done` |
| `claim-owner` | a review with a warning beside an address |
| `unknown-contract` | a danger for an unknown contract |
| `path-warning` | a danger for an unusual path |
| `typed-data` | details, then a review of the message when the person asks |
| `get-address` | a `verify_address` |
| `get-pubkey` | a `verify_pubkey` |
| `contract-data` | a review with a `data` field |
| `consent` | a review with a note only |
| `swap` | a final review with amounts, a caution and five extras, then `done` |
| `fee-bump` | a final review with a transaction ID and fees, and an extra, then `done` |
| `sign-message` | a final review with an address and a message, then `done` |
| `verify-message` | a review, then `done` |
| `signing-progress` | a `progress`, with the label changing per step, then `done` |

### Run by hand

Build the emulator and the app as above, start the emulator (`core/emu.py`),
then run one endpoint at a time:

```sh
sdk/apps/testapp/host/testappctl --help
sdk/apps/testapp/host/testappctl review --field "address:Recipient=TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq" --answer strong
sdk/apps/testapp/host/testappctl summary --amount "Amount=1.5 TRX" --fee "Fee=0.1 TRX"
sdk/apps/testapp/host/testappctl showcase unknown-contract
sdk/apps/testapp/host/testappctl stream-data --length 1025
```

`testappctl showcase --help` lists the names. The app is loaded afresh each run,
so a rebuilt app is what runs; `--no-reload` skips that. Like `trezorctl`, it
talks to the device at `TREZOR_PATH` (such as `udp:127.0.0.1:32500` for an
emulator started with `-P 32500`), or to the first one it finds.

### Host library

`host/testapp_host` is the client library: it loads the app, sends one request
and returns the answer, builds the facts, and its `messages` module is
generated from `protob/*.proto` by `cargo app-tool gen-py` (regenerated whenever
a `.proto` is newer), so both sides of the wire always agree. `showcases.py` holds
the example flows, composed from the endpoints; `cli.py` is a frontend over both,
and the device tests build their requests with it too.
