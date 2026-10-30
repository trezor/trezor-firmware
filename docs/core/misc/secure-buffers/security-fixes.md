# Secure buffers: typed key records and binary mnemonic fixes

Three weaknesses found in the security review of
`secure-buffers-poc_usb-tx-fix` (October 2026), and how to fix them. All
originate in `db0bc75ffb feat(core): execute private crypto in kernel` and are
inherited by every later checkpoint, including `_integration` and
`_usb-tx-fix`.

| | Finding | Severity | Attacker | Fixed by |
| --- | --- | --- | --- | --- |
| 1 | Wallet master key extraction by signing with one key on two curves | Critical | Compromised coreapp | [Typed key records](#fix-for-findings-1-and-2-typed-key-records) |
| 2 | Cardano private key extraction by pairing a real scalar with a chosen prefix | Critical | Compromised coreapp | [Typed key records](#fix-for-findings-1-and-2-typed-key-records) |
| 3 | Planted binary mnemonic (`0x0125`) substitutes the Cardano wallet | High | Compromised coreapp, once | [Kernel-derived binary mnemonic](#fix-for-finding-3-kernel-derived-binary-mnemonic) |

All three assume the threat model of the
[secure buffers architecture](../secure-buffers-poc.md): coreapp may be
compromised, and the kernel must keep the wallet seed confidential and intact
regardless. None of them exists as a separate problem on `main`, where a
compromised coreapp can already read the seed.

Implementation proceeds in [steps](#implementation-steps); steps 1 and 2 are
done.

## Finding 1: one key signing on two curves

### The weakness

The kernel treats every `SECRET_BYTES` record of 32 bytes as a key for any
operation that accepts 32 bytes. The same record is accepted by:

| Operation | Use of the 32-byte record |
| --- | --- |
| `VAULT_SIGN` | secp256k1 ECDSA private key |
| `VAULT_NIST_SIGN`, `VAULT_NIST_PUBLIC` | NIST P-256 private key (secp256k1 with `arg & 2`) |
| `VAULT_SCHNORR_*` | BIP-340 private key |
| `VAULT_ED_PUBLIC`, `VAULT_ED_SIGN` | Ed25519 seed |
| `VAULT_ED_SIGN_EXT` | Ed25519 expanded scalar, or its prefix |
| `VAULT_ECDH` | secp256k1, NIST P-256 or X25519 scalar |
| `VAULT_THP_PUBLIC`, `VAULT_THP_DH` | X25519 scalar |
| `VAULT_HMAC_TAG` | HMAC key (any length) |
| `VAULT_CHACHA_*`, `VAULT_AES_CBC` | Symmetric key |

`VAULT_SNAPSHOT` copies the private scalar of any node into such a generic
record. So a wallet node's private key, once snapshotted, can be used on any
curve and as any kind of key.

Using one key with several algorithms is only safe if the algorithms do not
interact. Two of them do: ECDSA on secp256k1 and ECDSA on NIST P-256.

### Why the two ECDSA curves interact

Both signing paths derive the nonce deterministically with RFC 6979
(HMAC-DRBG over SHA-256). The DRBG input is only the private key and the digest:

- NIST P-256 uses trezor-crypto `ecdsa_sign_digest()`, which seeds the DRBG with
  `init_rfc6979(priv_key, digest)`. The curve parameter only reduces the digest
  modulo the curve order.
- secp256k1 uses libsecp256k1-zkp `secp256k1_nonce_function_rfc6979`, the same
  HMAC-DRBG over `key || message`.

For one key `d` and one digest `z` (smaller than both curve orders, which holds
for almost every digest), both paths therefore draw the same first candidate
nonce `k`. It is accepted on both curves unless it exceeds an order, which
happens with probability below 2^-32. The signatures are then:

```
s1 = k^-1 (z + r1 d)  mod n1      (secp256k1, r1 = x(k G1) mod n1)
s2 = k^-1 (z + r2 d)  mod n2      (NIST P-256, r2 = x(k G2) mod n2)
```

There are two unknowns, `k` and `d`, both below 2^256, and two linear equations
over different prime moduli:

```
k ≡ a1 + b1 d  (mod n1),   a1 = z / s1,  b1 = r1 / s1
k ≡ a2 + b2 d  (mod n2),   a2 = z / s2,  b2 = r2 / s2
```

By the Chinese remainder theorem this is one congruence `k ≡ A + B d (mod N)`
with `N = n1 n2 ≈ 2^512`. The pairs `(d, k - A)` satisfying it form a
two-dimensional lattice with basis `(1, B)`, `(0, N)` and determinant `N`. The
true pair lies in a box of area about 2^512, the same as the determinant, so it
is one of very few lattice points near the box centre. Lagrange (Gauss)
reduction followed by Babai rounding and a search of a few neighbouring points
finds it. Each candidate `d` is checked against the public key.

Both implementations normalize `s` to the lower half of the order, so each
signature fixes `k` only up to sign. The attacker tries the four sign
combinations. The whole computation takes well under a second.

### The attack

Every step is an ordinary vault call that coreapp is allowed to make:

1. `VAULT_FROM_SEED` with `arg = 1`, on the sealed seed record: the master node.
2. `VAULT_PUBLIC` on the master node: master public key and chain code.
3. `VAULT_SNAPSHOT` on the master node: the master private key, as a generic
   32-byte record.
4. `VAULT_SIGN` and `VAULT_NIST_SIGN` with that record, on the same digest.
5. Offline: solve for `d` as above. With the chain code from step 2, the
   attacker has the master extended private key, which controls every account
   of every coin.

All of these operations are also allowed while the device is locked, for a
request holding the CoinJoin lock grant.

Verified on `_usb-tx-fix` (head `524980d0e9`, with this review's other fixups):

- A native test drove the real `vault_dispatch()` through steps 1–4. The key
  recovered from its two signatures equalled the BIP-32 master key computed
  independently from the seed, and the chain code matched.
- A standalone simulation of both nonce derivations recovered 10 of 10 random
  keys.

The same pattern applies to any snapshot, not only the master node.


## Finding 2: Ed25519 scalar paired with a chosen prefix

### The weakness

Cardano keys are Ed25519 *expanded* keys: a scalar `kL` and a 32-byte prefix
`kR`. RFC 8032 signing with an expanded key computes:

```
r = SHA-512(kR || M)        mod L     (the nonce)
R = r B
S = r + SHA-512(R || A || M) a   mod L     (a = kL as a scalar, A = a B)
```

The nonce depends only on the prefix and the message. Whoever knows `kR` knows
`r` for every message, and one signature then gives the scalar:

```
a = (S - r) * SHA-512(R || A || M)^-1   mod L
```

The secrecy of `kR` is therefore as important as the secrecy of `kL`.

`VAULT_ED_SIGN_EXT` takes the scalar and the prefix as two independent records
(`blob` and `extension`). It checks only that each is a 32-byte
`SECRET_BYTES` record of an accessible owner. Nothing ties the prefix to the
scalar, so coreapp can supply a prefix of its own.

### The attack

Every step is an ordinary vault call that coreapp is allowed to make:

1. `VAULT_CARDANO` with a sealed seed (SLIP-23, `arg = 0x101`), or any other
   path to a Cardano node, for example an account node derived with
   `VAULT_DERIVE`.
2. `VAULT_SNAPSHOT` with `arg = 0` on that node: the real scalar `kL`, as a
   generic record. This is what `node.private_key()` does for Cardano signing.
3. `VAULT_IMPORT_BYTES` with 32 bytes chosen by coreapp: a known prefix.
4. `VAULT_ED_SIGN_EXT` with the real scalar and the known prefix, on any
   message.
5. Offline: compute `r = SHA-512(prefix || M) mod L` and solve for `a` as
   above.

With `a`, the attacker can sign for that key with any prefix, because a
verifier checks only `S B = R + h A`. Cardano non-hardened derivation needs only
the parent scalar and the public chain code, so the scalar of an account node
gives the scalar of every address below it. Coreapp can derive and snapshot any
account. `VAULT_ED_SIGN_EXT` is also allowed while the device is locked, for a
request holding the CoinJoin lock grant.

Verified on `_usb-tx-fix` (head `524980d0e9` plus this review's fixups): a
native test drove the real `vault_dispatch()` and `vault_dispatch_message()`
through steps 1–4. The scalar recovered from the single signature reproduced
the node's public key (`a B = A`), and `r B` equalled the signature's `R`.

## Fix for findings 1 and 2: typed key records

### Principles

The design follows from both findings and from an independent review proposal
that reached the same conclusions:

- The kernel selects the curve and algorithm from authenticated record data,
  never from the request.
- Coreapp never supplies a nonce, a nonce seed, a domain or a nonce profile.
- Each signature scheme keeps its specified nonce construction: RFC 6979 for
  ECDSA, the BIP-340 tagged hashes, RFC 8032 for Ed25519.
- An Ed25519 expanded key is used only as one object; its scalar and prefix
  never exist as separate records.
- A record's type survives every copy: snapshot, clone and `VAULT_RETAIN`.

### Record header

The record header currently is:

```
offset  0      4     5       6      8
        owner  kind  length  zero   (GCM: nonce u64)
```

`secret_open()` already rejects records whose bytes 6 and 7 are not zero, and
`secret_aad()` authenticates the whole header. Byte 6 becomes the key type:

```
offset  0      4     5       6     7         8
        owner  kind  length  type  reserved  (GCM: nonce u64)
```

Because the header is part of the authenticated data, a client cannot change
the type without breaking the tag. Byte 7 stays zero, reserved for per-record
restrictions should they ever be needed. Records do not outlive a boot, so the
change needs only a `VAULT_ABI` bump, with no migration. ECB records are not
authenticated, but ECB builds are already refused in production.

### Key types

The type fixes both the curve and the representation of the secret. A
`static const` kernel table maps each type to the operations that accept it.

| Type | Size | Produced by | Accepted by | Import |
| --- | --- | --- | --- | --- |
| `NODE` | node | `FROM_SEED`, `DERIVE`, `IMPORT_NODE`, `CARDANO` | node operations; the node's own curve decides | node import only |
| `SEED` | 16–64 | `SEED_STORAGE`, import | `FROM_SEED`, `SLIP21` root, `CARDANO` sealed input (modes 1, 2) | yes |
| `SLIP21_NODE` | 64 | `SLIP21` node output, import | `SLIP21` (non-root) | yes |
| `SYMMETRIC` | ≤ 160 | `SLIP21` key output, `KEYVALUE_DERIVE`, `NEM_SHARED`, import | `HMAC_TAG`, `CHACHA_*`, `AES_CBC` | yes |
| `SECP256K1` | 32 | `SNAPSHOT` of a secp256k1-family node, `SCHNORR_GENERATE`, `SCHNORR_TWEAK`, import | `ECDSA_SIGN`, `SCHNORR_*`, `ECDH`, `ECDSA_PUBLIC` | yes |
| `NIST256P1` | 32 | `SNAPSHOT` of a NIST P-256 node, import | `ECDSA_SIGN`, `ECDH`, `ECDSA_PUBLIC`, `HMAC_TAG` (U2F key handles) | yes |
| `ED25519_SEED` | 32 | `SNAPSHOT` of an Ed25519-family node, import | `ED_PUBLIC`, `ED_SIGN` | yes |
| `X25519` | 32 | `THP_DERIVE`, `SNAPSHOT` of a Curve25519 node, import | `THP_PUBLIC`, `THP_DH`, `ECDH` | yes |
| `THP_DEVICE` | 16 | `THP_STORAGE`, import | `THP_DERIVE`, `SLIP21` root (not export) | yes |
| `CARDANO_SECRET` | 96 | `CARDANO` modes 3, 4, import | `CARDANO` sealed input (mode 0) | yes |

Rules behind the table:

- **One type per curve, not per algorithm.** secp256k1 ECDSA, BIP-340 and ECDH
  may share a key: BIP-340 derives its nonce with tagged hashes that differ from
  RFC 6979, and ECDH reveals no nonce. Bitcoin already uses keys this way.
- **Ed25519 and Ed25519-Keccak may share a seed.** Both derive the nonce from a
  hash of the secret prefix and the message, with different hashes, so one key
  and message never give two signatures with one nonce.
- **Symmetric uses share one type.** HMAC, ChaCha20 and AES are pseudorandom
  functions or permutations, and their outputs do not reveal the key. What
  matters is keeping wallet secrets out of them, which the other types do.
- **One exception: U2F key handles.** The U2F key-handle format, as on `main`,
  MACs the request with the credential's NIST P-256 private key, so `HMAC_TAG`
  also accepts `NIST256P1`. HMAC output reveals nothing about its key, and
  HMAC keyed with the scalar has nothing in common with the RFC 6979 nonce
  derivation, which uses the scalar only as HMAC input.
- **Imports.** `IMPORT_BYTES` takes the type from the request and may choose
  any type except `NODE` (nodes are imported with `IMPORT_NODE`). Coreapp
  supplied the plaintext, so whatever the kernel computes from it reveals
  nothing coreapp did not know. An imported record is dangerous only when an
  operation combines it with a record coreapp does not know, as finding 2 did;
  once `VAULT_ED_SIGN_EXT` takes a single node, no operation combines two
  records. An earlier version of this design forbade importing kernel-created
  types; that restriction protected nothing and broke tests that import known
  seeds.
- **Snapshots.** `SNAPSHOT` takes the type from the node's curve, which is part
  of the authenticated node encoding, so the client cannot choose it.
  `SNAPSHOT` refuses Cardano nodes, and `SNAPSHOT` with `arg = 1` (the prefix
  alone) is removed. A Cardano key leaves its node only as a signature.
- **Retention.** `VAULT_RETAIN` and clones keep the type.

### Operations

**ECDSA.** One signing operation, `ECDSA_SIGN`, replaces `VAULT_SIGN` and
`VAULT_NIST_SIGN`:

1. Open the key and check owner, caller, unlock state and the type's
   permission to sign.
2. Take the curve from the type (`SECP256K1`, `NIST256P1`), or from the node's
   curve when signing from a node in place, as `VAULT_SIGN` already does for
   secp256k1 nodes.
3. Select the nonce construction internally (see below).
4. Sign, and apply the requested output format. The canonical-form selector
   (Ethereum, EOS) is accepted for secp256k1 only.
5. Erase temporary state.

The request carries no curve. The implementation keeps the old operation
numbers for compatibility: `VAULT_SIGN` accepts only `SECP256K1` keys and
secp256k1 nodes, `VAULT_NIST_SIGN` only `NIST256P1` keys, so each number is
checked against the key's type.
`VAULT_NIST_PUBLIC` likewise becomes `ECDSA_PUBLIC` with the curve taken from the
type, and `VAULT_ECDH` takes its curve from the type and refuses a mismatching
`arg`.

**Ed25519 expanded keys.** `VAULT_ED_SIGN_EXT` takes one record: a Cardano
`NODE`. Its encoding already binds `kL` (private key) and `kR` (private key
extension) under one authentication tag, so the kernel signs from the node in
place and the scalar and prefix can never be mixed. The `extension` field of
the message request goes away.

**BIP-340 and plain Ed25519** keep their own operations and their specified
nonce constructions. A shared custom nonce prefix across schemes would break
conformance with BIP-340 and RFC 8032.

### Nonce domain for NIST P-256

With typed records, no API path can use one scalar on two curves. As a backstop
against a bypassed type check, from a bug or a fault, the kernel also makes the
two ECDSA nonce streams independent.

Separating one curve is enough, and NIST P-256 is the cheap side. Its kernel
signing path uses RFC 6979 with additional data (RFC 6979 §3.6):

```
k' = SHA-256("Trezor/vault/ecdsa-nonce/v1/nist256p1")
K  = HMAC_K(V || 0x00 || int2octets(x) || bits2octets(h1) || k')
K  = HMAC_K(V || 0x01 || int2octets(x) || bits2octets(h1) || k')
```

The rest of RFC 6979 is unchanged, including the retry for an out-of-range
candidate. The digest that is signed is unchanged.

Implementation: trezor-crypto gains `init_rfc6979_ext()` with an additional-data
input and an `ecdsa_sign_digest` variant that uses it. Only the kernel's NIST
P-256 path calls them; every other caller, and legacy, keeps plain RFC 6979.
The domain is a kernel constant; no request field reaches it.

secp256k1 keeps plain RFC 6979:

- every secp256k1 signature would otherwise change, across thousands of
  exact-signature device-test fixtures (`serialized_tx`, Ethereum and others);
- core would stop matching legacy (Trezor One), which shares many of those
  fixtures and keeps plain RFC 6979;
- the secp256k1-zkp backend already uses the RFC 6979 additional-data input to
  encode signing retries, so a domain would have to be combined with it;
- other tools could no longer reproduce Trezor's secp256k1 signatures.

NIST P-256 signatures change. They are used by FIDO/U2F, where they are
verified rather than compared, and by `SignIdentity` (SSH, GPG). The NIST P-256
case of `tests/device_tests/misc/test_msg_signidentity.py` pins an exact
signature and runs on every model, so it needs separate expected values for
core and Trezor One.

### Design choices

**A one-byte type instead of a per-record policy structure.** The review
proposal suggested storing `{curve, representation, allowed_operations}` in
each record. Only the kernel sets that policy, always from the operation that
produced the record, so it is a function of curve and representation. A type
indexing a kernel table gives the same guarantees, fits the existing
authenticated header bytes and cannot drift between records. A 32-bit
operation mask would not fit without growing the header, which changes the
blob size, the authenticated-data layout and every binding.

**Rejected alternatives.**

- *A curve-specific nonce for both curves, without types.* It breaks
  finding 1, but not finding 2 or other cross-type uses, and it changes every
  secp256k1 signature.
- *Removing `SNAPSHOT`.* Coreapp signs with snapshots for most coins, and other
  32-byte records would still cross types.
- *A separate `ED25519_EXPANDED` type for `kL || kR`.* It works, but signing
  from the Cardano node needs no new type and no copy of the key.

### Changes

**Kernel (`core/embed/sec/vault`).**

- `secret_seal()` takes a type and writes byte 6; `secret_open()` takes the
  accepted types and checks them before and after decryption, like the
  existing owner check.
- The operation-to-type table replaces the scattered checks (record lengths,
  `node_has_private_key`, the `b[4]` dispatch in `VAULT_SIGN`).
- `ECDSA_SIGN` and `ECDSA_PUBLIC` as above; `VAULT_ED_SIGN_EXT` signs from a
  Cardano node; `SNAPSHOT` sets types and refuses Cardano nodes.
- `VAULT_ABI` bump.

**trezor-crypto.** `init_rfc6979_ext()` and the ECDSA variant using it.

**Coreapp bindings (`core/embed/upymod/modtrezorcrypto`).** Pass a type wherever
`IMPORT_BYTES` is called. `ed25519.sign_ext()` takes the node instead of
`private_key()` and `private_key_ext()`, and `HDNode.private_key_ext()` is
removed. Its three callers in `apps/cardano` (`sign_tx/signer.py`,
`sign_message.py`, `auxiliary_data.py`) change accordingly. Other coins keep
`node.private_key()`, whose result is now typed.

### Tests

- Both attacks as native regression tests: `ECDSA_SIGN` on NIST P-256 with a
  secp256k1 snapshot fails, and `VAULT_ED_SIGN_EXT` accepts nothing but a
  Cardano node.
- Each type is refused by every operation outside its row.
- A record with a modified type byte fails authentication.
- The type survives snapshot, clone and `VAULT_RETAIN`.
- NIST P-256: new vectors for the separated nonce, a check that its nonce
  differs from plain RFC 6979 for the same key and digest, and that
  verification still succeeds.
- secp256k1: existing vectors unchanged, canonical-form retries still work.
- Device tests for every coin cover the legitimate paths.

## Fix for finding 3: kernel-derived binary mnemonic

### The weakness

`0x0102` holds the mnemonic words. `0x0125` holds the same mnemonic as raw bits
(entropy plus checksum), written by `store_binary_mnemonic()` as
`mnemonic_to_bits(words)`. Nothing ever checks that the two agree.

On BIP-39 devices, Cardano Icarus and Icarus-Trezor accounts are derived from
`0x0125`. `cardano.derive_icarus(None, ...)` calls `VAULT_CARDANO` mode 4, which
reads `0x0125` and passes it with the passphrase to
`secret_from_entropy_cardano_icarus()`. Icarus-Trezor is the derivation Trezor
Suite uses by default. Whatever `0x0125` contains therefore decides which
Cardano accounts the device shows and signs for.

Coreapp cannot read `0x0125`. The write-once rule (fixup `cbab6d436b`) lets it
write a protected key once, while the key does not exist. That first write is
needed because the reset and recovery flows in Python store both keys. It is
harmless for `0x0102`, which always exists on an initialized device. `0x0125`,
however, can be missing on an initialized BIP-39 device:

- **The wallet was set up or recovered with Bitcoin-only firmware, then
  universal firmware was installed.** Bitcoin-only builds skip
  `store_binary_mnemonic()` and mark storage as current. The migration never
  runs, and `0x0125` stays missing for good.
- **The storage is version 2 and the migration has not run yet.** The
  migration (`_migrate_from_version_02()` calling
  `bip39.migrate_binary_mnemonic()`) is started by coreapp, so a compromised
  coreapp can skip it.
- Debug builds can load mnemonics that `mnemonic_to_bits()` rejects
  (`allow_derivation_fail`). Production is not affected.

### The attack

1. The attacker gets code execution in coreapp once, while the device is
   unlocked (private storage is writable only then), for example through a bug
   in a message parser.
2. They write entropy of their choice to `0x0125`. The write is allowed because
   the key does not exist.
3. The compromise ends: the device reboots, or the user installs fixed
   firmware. Storage survives firmware updates.
4. Honest firmware derives the Icarus-Trezor root from the planted entropy.
   Suite shows those Cardano addresses as the user's, and the device confirms
   them on screen and signs with them.
5. The user receives ADA at those addresses. The attacker knows the entropy,
   and the passphrase is empty for a standard wallet, so they can spend it at
   will.

The write-once rule makes it worse: honest firmware can neither overwrite nor
delete the planted value.

Nothing visible changes. The mnemonic and all other coins still come from
`0x0102`. The difference appears only if the user restores the mnemonic
elsewhere: the Cardano accounts there are empty.

The attacker does not learn the seed, cannot affect other coins, cannot affect
a passphrase wallet without knowing the passphrase, and cannot affect a device
that already has `0x0125`.

### The fix

Two parts. **B** removes the weakness; **A** removes the write path that made
it possible.

**B. Mode 4 derives the bits from the words.** In `VAULT_CARDANO` mode 4
(`vault.c`), replace the `storage_get(0x0125, ...)` call with:

1. `storage_get(0x0102, ...)` into a local buffer of 256 bytes, as
   `VAULT_SEED_STORAGE` and `VAULT_MNEMONIC` already do.
2. `mnemonic_to_bits(mnemonic, binary)`. The kernel already links it for
   `VAULT_MNEMONIC` arg 2. Fail the operation if it returns zero (words that
   are not a valid BIP-39 mnemonic) or reports more than 33 bytes.
3. Erase the words and the bits after use, on every path.

The kernel then never reads `0x0125`, so a planted or stale value has no
effect. The cost is 12 to 24 word lookups per derivation, negligible next to
the 4096 PBKDF2 iterations of the Icarus derivation that follows. Devices that
came from Bitcoin-only firmware, which today cannot derive Icarus accounts
because `0x0125` is missing, start working.

Mode 3, where coreapp supplies the bits itself, is unchanged: coreapp already
knows that input, so it learns nothing.

**A. Only the kernel writes `0x0125`.**

- `vault_storage_write_allowed()` refuses `0x0125` in every form, as it does for
  `0x0117` and `0x0129`. The emulator mirror in `modtrezorconfig.c` does the
  same.
- `store_binary_mnemonic()` in `core/src/storage/device.py` calls
  `bip39.migrate_binary_mnemonic()` instead of writing the bits.
  `VAULT_MNEMONIC` arg 2 already computes them from `0x0102` in the kernel and
  writes them.
- The kernel keeps writing `0x0125` only so that older firmware still finds it
  after a downgrade. Nothing in this firmware reads it.

With B in place, A is defence in depth. It also prevents a stale `0x0125` from
reaching an older firmware after a downgrade, for devices updated after this
fix.

### Tests

- Native or emulator unit test: store the mnemonic through `0x0102` only,
  without `0x0125`. `derive_icarus(None, ...)` must equal
  `derive_icarus(mnemonic_to_bits(words), ...)` for both Icarus variants.
- Coreapp writes to `0x0125` fail, both while it is missing and after it
  exists.
- Device tests: the Cardano address and signing tests on BIP-39 wallets, and
  the existing storage-upgrade tests.


## Implementation steps

These security-review work items are distinct from the five rollout stages in
[the architecture](../secure-buffers-poc.md#proposed-implementation-stages).
The current prototype contains the binary-mnemonic and typed-kernel-record
changes; intact-node Cardano signing and Cardano snapshot refusal are implemented.

Curve/operation restrictions and intact-node Cardano signing belong to the
first stage that exposes opaque signing values, including its transitional
coreapp backend. Kernel migration must preserve that contract rather than
repair an unsafe earlier opaque API. The binary-mnemonic source and write
rules belong with the storage-authority migration. P-256 nonce-domain
separation remains independent defense in depth and changes signature bytes.

The numbered items below retain the review breakdown. Their numbering does
not authorize a completed rollout stage to leave an earlier finding open.

### Step 1: kernel-derived binary mnemonic (finding 3)

**Kernel (`vault.c`).** A new helper, `vault_stored_mnemonic_bits()`, reads the
words from `0x0102` and converts them with `mnemonic_to_bits()`:

- It is `noinline`, so its 256-byte word buffer does not join the stack frame
  shared by all vault operations. The kernel stack is 8 KiB, and the
  `VAULT_CARDANO` case already holds a 96-byte secret and the 33-byte bits.
- It refuses words containing a NUL byte, an empty value or a value that does
  not fit the buffer, and erases the words on every path.
- It returns the length in bytes, or 0. A result over 33 bytes is treated as a
  failure; `mnemonic_to_bits()` cannot produce one for a valid BIP-39 mnemonic.

`VAULT_CARDANO` mode 4 uses the helper instead of `storage_get(0x0125, ...)`. A
failed conversion leaves the length at 0, and the existing length check then
fails the operation, as a missing `0x0125` did before. Mode 3, where coreapp
supplies the bits, is unchanged.

`vault_storage_write_allowed()` now allows coreapp exactly one protected write:
the first store of `0x0102`, under its canonical key. `0x0125` joins `0x0117`
and `0x0129` as kernel-only. The old rule allowed a first write of `0x0125`,
which was the root of finding 3.

**Emulator.** The `modtrezorconfig.c` mirror of the kernel rule refuses
`0x0125` in every form.

**Python (`storage/device.py`).** `store_binary_mnemonic()` keeps its
validation: it still converts the words with `mnemonic_to_bits()`, so invalid
words raise exactly as before, including the debug-only
`allow_derivation_fail` path used by `test_msg_loaddevice.py`. Instead of
writing the result, it calls `bip39.migrate_binary_mnemonic()`, and the kernel
writes the bits it computes itself from `0x0102`.

**Why the kernel still writes `0x0125`.** Nothing in this firmware reads it any
more. It is kept so that a device downgraded to older firmware, which reads
`0x0125`, still finds the value it expects.

**Effect on existing devices.**

- A value planted earlier is ignored from now on; the kernel never reads it.
- Wallets without `0x0125` (from Bitcoin-only firmware, or an unmigrated
  storage) can now derive Icarus accounts; before, that derivation failed.
- SLIP-39 wallets do not use mode 4 and are unaffected.

**Tests.**

- `test_apps.common.protected_seed.py`, new
  `test_icarus_ignores_binary_mnemonic_copy`: stores the words without
  `0x0125`, checks that coreapp cannot write `0x0125`, and checks that both
  Icarus variants derive the same keys as from `mnemonic_to_bits()` of the
  words.
- `test_trezor.crypto.vault.py`: writing `0x0125` now fails even when it is
  missing.
- All 147 core unit-test files pass, and the Cardano, load-device, BIP-39 reset
  and recovery, and backup device tests pass on the T3T1 emulator.

### Step 2: typed key records (finding 1)

**Record format.** Header byte 6 holds the type and byte 7 stays zero.
`secret_seal()` takes a type and derives the kind from it (`NODE` is a node,
everything else is bytes). `secret_open()` takes the set of accepted types,
checks the type, the matching kind and byte 7 before decryption, and checks the
type again after decryption, like the owner check. `VAULT_ABI` moves from
`27 + mode` to `31 + mode`, so an old client cannot talk to a new kernel.

**Operations.** Every `secret_open()` call states the types it accepts, and
every sealed result states its type, following the table above. The cases that
need care:

- `VAULT_RETAIN` reseals a request record for its session with the type the
  record already has, so retention can never change a type.
- `VAULT_SNAPSHOT` sets the type from the node's curve: secp256k1 family
  (`secp256k1`, Decred, Groestl, Smart) to `SECP256K1`, `nist256p1` to
  `NIST256P1`, Ed25519 family (including the Keccak and SHA-3 variants) to
  `ED25519_SEED`, `curve25519` to `X25519`. It refuses Cardano nodes; signing consumes the authenticated node directly.
- `VAULT_SLIP21` accepts `SEED` and `THP_DEVICE` for roots (the THP credential
  MAC derives its key from the device secret), `SEED` only for export, and
  `SLIP21_NODE` for non-root derivation. Its outputs are `SLIP21_NODE` and
  `SYMMETRIC`.
- `VAULT_NIST_PUBLIC` with `arg & 2` (a secp256k1 public key) accepts only
  `SECP256K1`, otherwise only `NIST256P1`. `VAULT_ECDH` takes the type matching
  its curve argument.
- The `VAULT_CARDANO` sealed input is accepted only in modes 0 (a
  `CARDANO_SECRET`), 1 and 2 (a `SEED`).
- `VAULT_HMAC_TAG` accepts `SYMMETRIC` and, for U2F, `NIST256P1`.
- `VAULT_IMPORT_BYTES` takes the type in `arg` and refuses 0, `NODE` and values
  past the last type. The range is checked before the type is used as a shift
  count: `arg` comes straight from the request, and a shift by 32 or more is
  undefined behaviour in C. The MicroPython constructor checks the range too,
  but a direct syscall bypasses it.
- In ECB builds the header is not authenticated, so a client can relabel a
  record. ECB is already refused in production; typed records protect only
  authenticated builds.

**Coreapp.** `secbytes(value, type)` passes the type to `IMPORT_BYTES`; the
default is `secbytes.SYMMETRIC`, the safest choice. The types are class
constants of `secbytes`. Before, a populated value refused a second argument
(it was the capacity of an empty holder); now it is the key type. The BIP-340
binding, the only C binding that imports plaintext, uses `SECP256K1`.

**Tests changed by this step.**

- Unit tests that import signing keys or seeds pass the matching type, and the
  shared `cache_seed()` helper imports a `SEED`.
- `test_trezor.crypto.vault_misc.py` used one imported key for ECDH on
  secp256k1, NIST P-256 and Curve25519, the exact cross-curve use this step
  forbids. It now imports one key per curve and checks that each curve refuses
  the other keys.
- The shared `assert_secret()` helper compared any secret by using it as an
  HMAC key. Its only callers checked the two halves of Cardano expanded keys.
  It is replaced by `assert_cardano_key()`, which makes two checks:
  - A vault `sign_ext` signature must equal a plaintext reference signature.
    A deterministic Ed25519 signature depends on both halves, but on the
    scalar only modulo the group order, so scalars differing by the order
    sign identically.
  - A hardened child of the node must equal a hardened child of a plaintext
    reference node. Hardened derivation hashes the exact bytes of both
    halves.

  `test_key_check_compares_exact_scalar_bytes` checks that a scalar shifted
  by the group order signs identically but fails the helper.
- The native tests give every import a type, and the direct `secret_open()` and
  `secret_seal()` calls pass types instead of kinds.
- New native test `key_types()`, in `vault_key_types.h`, included by both
  `test_vault.c` and `test_vault_saes.c` so it runs in all six sealing modes
  (the runner builds the SAES suite instead of `test_vault.c` for the SAES
  modes). It checks that the finding 1 signature pair
  is refused, that every other cross-type use of a secp256k1 key and of a seed
  is refused while the legitimate ones work, that imports cannot create nodes
  or invalid types (including 32, 33 and `UINT32_MAX`, under UBSan), that
  retention keeps the type, and (in authenticated modes) that a relabelled
  record fails.

**Why this step alone fixes finding 1.** A snapshot of a secp256k1 node is a
`SECP256K1` record, and `VAULT_NIST_SIGN` refuses it, so the attacker can no
longer obtain two signatures with one scalar on two curves.

### Step 3: Cardano signing from the node (implemented; finding 2)

`VAULT_ED_SIGN_EXT` opens one `NODE` record, requires the Cardano curve and a
private key, and signs with the node's own private key and private key
extension. The extension field of the message request must be zero.
`VAULT_SNAPSHOT` refuses Cardano nodes and no longer accepts `arg = 1`.
The legacy two-opaque-record request is rejected, including a valid node plus
an independently supplied extension. The mode-specific vault ABI is bumped;
Cardano reference signatures remain unchanged.

`ed25519.sign_ext(node, message)` takes the node, `HDNode.private_key_ext()` is
removed, and the three Cardano callers (`sign_tx/signer.py`,
`sign_message.py`, `auxiliary_data.py`) pass the node. The contract is established with wallet activation and preserved when
operations move into the kernel. These fix numbers are distinct from rollout
stages.

### Step 4: nonce domain for NIST P-256

Adds `init_rfc6979_ext()` and an ECDSA variant to trezor-crypto, and uses them
in the kernel's NIST P-256 signing only. It changes NIST P-256 signature bytes,
so it also updates the expected signatures in
`tests/device_tests/misc/test_msg_signidentity.py` for core models. Kept last
and separate: steps 1–3 remove both attacks without it, and it is the only step
that changes signatures.

## Relevance to main

The question for each fix: does `main` have the weakness, given that on `main`
coreapp and the kernel are one trusted program?

| Item | On `main` | Recommendation |
| --- | --- | --- |
| Finding 1: one key on two curves | Not exploitable | Secure buffers only |
| Finding 2: Ed25519 scalar with a chosen prefix | Not exploitable | Secure buffers only |
| Finding 3, security part: planted `0x0125` | Not meaningful | Secure buffers only |
| Finding 3, function part: Icarus fails without `0x0125` | Present | Candidate for `main` |
| NIST P-256 nonce domain | Not needed | Secure buffers only |
| USB TX lifetime fix (`db790efde7`) | Present | Candidate for `main` |

**Finding 1 on `main`.** The weakness needs one private scalar used on two
curves. On `main`, every private key is derived from the seed for one curve:
`hdnode_from_seed()` keys the master derivation with a curve-specific string
(`Bitcoin seed`, `Nist256p1 seed`, ...), so the secp256k1 and NIST P-256 trees
of one wallet have unrelated scalars. No message lets the host supply a private
key. That RFC 6979 does not depend on the curve is standard behaviour of the
algorithm, not a bug in trezor-crypto. Only the vault, which lets a client
re-type a scalar, turned it into a weakness.

**Finding 2 on `main`.** Cardano signing on `main` calls
`ed25519.sign_ext(node.private_key(), node.private_key_ext(), ...)` with both
halves of the same node, in code the attacker does not control. The host cannot
supply a prefix. Signing from the node would be a reasonable API cleanup on
`main`, but it fixes nothing there.

**Finding 3 on `main`.** A compromised firmware on `main` can read the
mnemonic itself and leak it, which is strictly worse than planting `0x0125`. The
security part therefore adds nothing on `main`. The functional part does:
`mnemonic.derive_cardano_icarus()` on `main` raises
`RuntimeError("Failed to get binary mnemonic.")` when `0x0125` is missing, and
nothing recreates it once the storage is at the current version. A Bitcoin-only
firmware stores the words but not `0x0125`, and marks the storage current. If
the universal firmware is then installed without a storage wipe, Cardano
derivation fails until the device is wiped and recovered. Whether the
bootloader keeps storage across that switch depends on the vendor headers of
the two firmwares (on T2T1 both use the same vendor header) and needs to be
confirmed on a device. If it does, `main` should derive the bits from the words
whenever `0x0125` is missing, or always.

**USB TX lifetime fix.** Its commit message states that the race "exists
independently of secure buffers": the WebUSB and HID write handlers pass
caller-owned memory to an asynchronous transfer. That is a `main` bug, and the
fix and its native test can go to `main` as they are. The WebUSB read timeouts
seen on `main`'s nightly hardware runs are a different symptom (no response,
not a corrupted header), so this fix should not be expected to cure them.

**Everything else from this review** (backup disclosure gating, the CoinJoin
lock grant, the delete guard, the kernel ECC context, one-call ChaCha
decryption, the sealed seed cache, typed records) concerns the boundary between
coreapp and the kernel. It exists only with secure buffers.
