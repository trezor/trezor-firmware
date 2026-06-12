# apps/darkfi — known limitations / future work

These are deliberate, documented gaps in the current DarkFi (DRK) hardware-custody
app. Both are noted in the feature commit and in `messages-darkfi.proto`; this file
tracks them so they are not forgotten.

## 0. Key derivation: DarkFi HD from the BIP-39 seed (by design)

DRK keys are derived with DarkFi's own hierarchical-deterministic scheme
(`crypto/hd.rs`, mirrored in `crypto/pallas_drk.c` / `pallas.hd_account`) rooted
directly at the device's **BIP-39 seed**, indexed by a DarkFi `account` number —
*not* via a BIP-32/SLIP-44 path. This is intentional: the same scheme runs in the
`drk` software wallet, so one mnemonic restores the identical spend keys on the
device and in `drk`. The cross-repo derivation contract and reference vectors live
in `darkfi/doc/src/dev/trezor_drk_test_vectors.md` and are asserted by
`crypto/tests/test_pallas.c`.

## 1. Full bs58check address rendering is host-side

A canonical DarkFi address string is
`base58check( [prefix] || pk_d || blake3(prefix || pk_d)[:4] )`.

The inner checksum uses **BLAKE3**, which is **not** available in device firmware
(`crypto/` ships BLAKE2b and SHA-2 only). Vendoring a full BLAKE3 implementation
is a non-trivial amount of unaudited-on-device crypto, so it is intentionally out
of scope for now.

- **Current behavior:** `DarkfiGetAddress` returns the raw 32-byte `pk_d`
  (compressed Pallas point). The device shows `pk_d` in hex; the host (`drk`)
  assembles and displays the canonical bs58check address, which it can already do.
- **Future work:** vendor BLAKE3 into `crypto/` (and a `trezorcrypto` binding),
  then render the full address string + QR on-device in `get_address.py`.

## 2. Trustless binding of displayed spend details to the signed sighash

`DarkfiSignSpendAuth` shows the user `value` / `token_id` / `recipient` from
`DarkfiSpendDetails`. These are **host-supplied cleartext for display** — the
signature itself is over the transaction `sighash`, which commits to the *hidden*
coin/value commitments, not to these plaintext fields.

A fully trustless binding would require the device to **recompute the transaction
sighash from its components on-device** (coin commitment via 7-input Poseidon,
value/token Pedersen commitments, Merkle root, etc.) and check it equals the
`sighash` it is asked to sign. That is a substantial amount of on-device
transaction modeling and is future work.

- **Current mitigation:** the device **always also displays the exact `sighash`
  it signs** (`confirm_blob`, hold-to-confirm). A malicious host therefore cannot
  show benign details while signing a *different* message than the one displayed;
  it could at most mislabel the (correct, shown) sighash. The host `drk` is the
  party that maps details↔sighash today.
- **Future work:**
  - expose a general N-input `poseidon_hash` binding (currently only hash2/hash3),
  - reconstruct the coin commitment
    `poseidon([pk_x, pk_y, value, token_id, spend_hook, user_data, blind])`
    and the value/token commitments on-device,
  - recompute the tx sighash and assert it matches before signing,
  - then the displayed `DarkfiSpendDetails` are cryptographically bound to the
    signature.
