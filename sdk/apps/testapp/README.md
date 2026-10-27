# testapp

A test-only app that exposes every SDK crypto function (`trezor_app_sdk::crypto`)
to the host, so device tests can exercise the crypto API end to end: from the
app, through the app API, to Core.

**Never ship it.** It is dev-signed only and must stay out of every release
bundle.

## How it works

Each wire request names one crypto function and carries its parameters one to
one (`protob/testapp.proto`). The app calls the function and answers with its
result. An error the function returns comes back to the host as a `Failure`
whose code is the SDK's `Error::code()`; the app keeps running.

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

## Device tests

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
