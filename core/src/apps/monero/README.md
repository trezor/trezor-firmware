# Monero

MAINTAINER = ...

AUTHOR = Dusan Klinec <dusan.klinec@gmail.com>

REVIEWER = Tomas Susanka <tomas.susanka@satoshilabs.com>,
           Jan Pochyla <jan.pochyla@satoshilabs.com>,
           Ondrej Vejpustek <ondrej.vejpustek@satoshilabs.com>

-----

This Monero implementation was implemented from scratch originally for Trezor by porting Monero C++ code to the Python codebase.

The implementation heavily relies on the [trezor-crypto] Monero functionality which implements basic crypto primitives and
other Monero related functionality (e.g., monero base58, accelerated and optimized Borromean range signatures)

A general high level description of the integration proposal is described in the documentation: [monero-doc].

## Features

The implementation provides the following features:

### Transaction signature

Signs a Monero transaction on the Trezor.

- Designed so number of UTXO is practically unlimited (hundreds to thousands)
- Maximal number of outputs per transaction is 8 (usually there are only 2)
- Supports 8 B encrypted payment ID and 32 B unencrypted payment ID.

### Key Image sync

Key Image is computed with the spend key which is stored on the Trezor.

In order to detect if the UTXO has been already spent (thus computing balance due to change transactions)
and correct spending UTXOs the key images are required. Without the key images the Monero view only
wallet incorrectly computes balance as it sees all ever received transactions as unspent.

Key image sync is a protocol that allows to compute key images for incoming transfers by Trezor.

Example: 20 XMR in the single UTXO is received, thus real balance is 20. 1 XMR is sent to a different
address and remaining 19 are sent back with a change transaction. Correct balance is 19 but without
correct key image the view only wallet shows balance 39. Without knowing which UTXO is spent
the newly constructed spending transactions can pick already spent input. Such transaction is
rejected by a Monero daemon as a double spending transaction.

Normally, the Key image sync is not needed as the key image computation is done by
the transaction signing algorithm. However, if the wallet file is somehow corrupted
or the wallet is used on a new host / restored from the Trezor the key
image sync is required for correct function of the wallet. It recomputes key images
for all received transaction inputs.


## Integration rationale

The Monero codebase already contains cold wallet support. I.e., wallet not connected to the Internet, which should provide
better security guarantees as it minimizes attack surface compared to the hot wallet - always connected wallet.

As the cold wallet is not connected to the Internet and does not have access nor to the blockchain neither to the monero
full node the all information for transaction construction have to be prepared by the hot wallet.

When using the cold wallet, hot wallet is watch-only. It has only the view-key so it can scan blockchain for incoming
transactions but is not able to spend any transaction.

Transaction signature with cold wallet works like this:

- Create transaction construction data on hot wallet. `transfer <address> <amount>`. Works similar to the normal wallet operation
but instead of the signed transaction, the watch-only hot wallet generates `unsigned_txset` file which contains
transaction construction data.

- Cold wallet opens `unsigned_txset`, verifies the signature on the transaction construction data and creates Monero transaction
using the data. Cold wallet creates `signed_txset`

- Hot wallet opens `signed_txset`, verifies the transaction and asks user whether to submit transaction to the full node.

### Cold wallet protocols

As cold wallet support is already present in Monero codebase, the protocols were well designed and analyzed.
We decided to reuse the cold wallet approach when signing the transaction as the Trezor pretty much behaves as the cold wallet,
i.e., does not have access to the blockchain or full Monero node. The whole transaction is built in the Trezor thus
the integration has security properties of the cold wallet (which is belevied to be secure). This integration approach
makes security analysis easier and enables to use existing codebase and protocols. This makes merging Trezor support to
the Monero codebase easier.
We believe that by choosing a bit more high-level approach in the protocol design we could easily add more advanced features,

Trezor implements cold wallet protocols in this integration scheme.


## Description

Main high level protocol logic is implemented in `apps/monero/protocol/` directory.

### Serialization

The serialization in `apps/monero/xmr/serialize` is the cryptonote serialization format used to serialize data to blockchain.
The serialization was ported from Monero C++. Source comes from the library [monero-serialize].

Serialization scheme was inspired by protobuf serialization scheme.
Fields are specified as a classmethod which is easier to `gc.collect()` after serialization is done.

```python
    @classmethod
    def f_specs(cls):
        return (("size", SizeT),)
```

Serialization is synchronous.


### Protocols

Transaction signing and Key Image (KI) sync are multi-step stateful protocols.
The protocol have several roundtrips.

In the signing protocol the connected host mainly serves as a dumb storage providing values to the Trezor when needed,
mainly due to memory constrains on Trezor. The offloaded data can be in plaintext. In this case data is HMACed with unique HMAC
key to avoid data tampering, reordering, replay, reuse, etc... Some data are offloaded as protected, encrypted and authenticated
with Chacha20Poly1305 with unique key (derived from the protocol step, message, purpose, counter, master secret).

Trezor builds the signed Monero transaction incrementally, i.e., one UTXO per round trip, one transaction output per roundtrip.

### Protocol workflow

Key image sync and transaction signing protocols are stateful.
Both protocols implement custom workflow managing the protocol state and state transitions explicitly.

Entry to the protocol workflow is passed on the initial protocol message, i.e., only the initial protocol message
is registered via `wire.add()`. The workflow internally manages receiving / sending protocol messages.

Each finished protocol step specifies the next expected message set which helps to govern protocol state transitions,
i.e., exception is thrown if another message is received as expected.

As the protocols implement custom workflow the general package unimport in `wire` is not called which
could lead to memory problems as locally imported packages are not freed from memory on `gc.collect()`.
Thus protocols call unimport manually after processing the protocol messages.

Protobuf messages are following the convention `MoneroXRequest`, `MoneroXAck`.


## Key Image sync work flow

In the KI sync cold wallet protocol KIs are generated by the cold wallet. For each KI there is a ring signature
generated by the cold wallet (KI proof).

KI sync is mainly needed to recover from some problem or when using a new hot-wallet (corruption of a wallet file or
using Trezor on a different host).

The KI protocol has 3 steps.

### Init step

- `MoneroKeyImageExportInitRequest`
- Contains commitment to all KIs we are going to compute (hash of all UTXOs).
- User can confirm / reject the KI sync in this step. Init message contains number of KIs for computation.

### Sync

- `MoneroKeyImageSyncStepRequest`
- Computes N KIs in this step. N = 10 for now.
- Returns encrypted result, `MoneroExportedKeyImage`

### Finalization

- `MoneroKeyImageSyncFinalRequest`
- When commitment on all KIs is correct (i.e, number of UTXOs matches, hashes match) the encryption key is released
to the agent/hot-wallet so it can decrypt computed KIs and import it


## Transaction signing

For detailed description and rationale please refer to the [monero-doc].

- The protocol workflow `apps/monero/sign_tx.py`
- The protocol is implemented in `apps/monero/protocol/signing/`

### `MoneroTransactionInitRequest`:

- Contains basic construction data for the transaction, e.g., transaction destinations, fee, mixin level,
range proof details (type of the range proof, batching scheme).

After receiving this message:
- Trezor prompts user for verification of the destination addresses and amounts.
- Commitments are computed thus later potential deviations from transaction destinations are detected and signing aborts.
- Secrets for HMACs / encryption are computed, TX key is computed.
- Deprecated: Precomputes required sub-addresses (init message indicates which sub-addresses are needed).

### `MoneroTransactionSetInputRequest`

- Sends one UTXO to the Trezor for processing, encoded as `MoneroTransactionSourceEntry`.
- Contains construction data needed for signing the transaction, computing spending key for UTXO.

Trezor computes spending keys, `TxinToKey`, `pseudo_out`, HMACs for offloaded data

### `MoneroTransactionInputsPermutationRequest` (Deprecated)

UTXOs have to be sorted by the key image in the valid blockchain transaction.
This message caries permutation on the key images so they are sorted in the desired way.

In Client version 3+ sending the permutation is deprecated. Original sort index is sent from the host
when needed (to verify HMACs built on the original ordering). Moreover, permutation correctness is checked by
the set size, HMAC validity and strict ordering on the key images.

### `MoneroTransactionInputViniRequest`

- Step needed to correctly hash all transaction inputs, in the right order (permutation computed in the previous step).
- Contains `MoneroTransactionSourceEntry` and `TxinToKey` computed in the previous step.
- Trezor Computes `tx_prefix_hash` is part of the signed data.


### `MoneroTransactionAllInputsSetRequest`

- Sent after all inputs have been processed.
- Used in the range proof offloading to the host. E.g., in case of batched Bulletproofs with more than 2 transaction outputs.

### `MoneroTransactionSetOutputRequest`

- Sends transaction output, `MoneroTransactionDestinationEntry`, one per message.
- HMAC prevents tampering with previously accepted data (in the init step).
- Trezor computes data related to transaction output, e.g., range proofs, ECDH info for the receiver, output public key.
- In case offloaded range proof is used the request can carry computed range proof.

### `MoneroTransactionAllOutSetRequest`

Sent after all transaction outputs have been sent to the Trezor for processing.
Request is empty, the response contains computed `extra` field (may contain additional public keys if sub-addresses are used),
computed `tx_prefix_hash` and basis for the final transaction signature `MoneroRingCtSig` (fee, transaction type).

### `MoneroTransactionMlsagDoneRequest`

Message sent to ask Trezor to compute pre-MLSAG hash required for the signature.
Hash is computed incrementally by Trezor since the init message and can be finalized in this step.
Request is empty, response contains message hash, required for the signature.

### `MoneroTransactionSignInputRequest`

- Caries `MoneroTransactionSourceEntry`, similarly as previous messages `MoneroTransactionSetInputRequest`, `MoneroTransactionInputViniRequest`.
- Caries computed transaction inputs, pseudo outputs, HMACs, encrypted spending keys and alpha masks
- Trezor generates MLSAG for this UTXO, returns the signature.
- As output masks are deterministic, the pseudo output balancing is performed in this step (sum of input masks equal to the sum of output masks).
- Multisig is not supported.

### `MoneroTransactionFinalRequest`

- Sent when all UTXOs have been signed properly
- Finalizes transaction signature
- Returns encrypted transaction private keys which are needed later, e.g. for TX proof. As Trezor cannot store aux data
for all signed transactions its offloaded encrypted to the wallet. Later when TX proof is implemented in the Trezor it
will load encrypted TX keys, decrypt it and generate the proof.
- Since Client v3+ the final response contains opening encryption key to decrypt signatures generated in the previous step.


## Implementation notes

Few notes on design / implementation.

### Cryptography

Operation with Ed25519 points and scalars are implemented in [trezor-crypto] so the underlying cryptography layer
is fast, secure and constant-time.

Ed Point coordinates are Extended Edwards, using type `ge25519` with coordinates `(x, y, z, t)`. Functions in Monero code
in the [trezor-crypto] use the `ge25519` for points (no other different point formats).

Functions like `op256_modm` (e.g., `add256_modm`) operate on scalar values, i.e., 256 bit integers modulo curve order
`2**252 + 3*610042537739*15158679415041928064055629`.

Functions `curve25519_*` operate on 256 bit integers modulo `2**255 - 19`, the coordinates of the point.
These are used mainly internally (e.g., for `hash_to_point()`) and not exported to the [trezor-core].

[trezor-crypto] contains also some Monero-specific functions, such as
`xmr_hash_to_scalar`, `xmr_hash_to_ec`, `xmr_generate_key_derivation`. Those are used in [trezor-core] where more high
level operations are implemented, such as MLSAG.

#### Crypto API

API bridging [trezor-crypto] and [trezor-core]: `embed/extmod/modtrezorcrypto/modtrezorcrypto-monero.h`

It encapsulates Ed25519 points and scalars in corresponding Python classes which have memory-wiping destructor.
API provides basic functions for work with scalars and points and Monero specific functions.

The API is designed in such a way it is easy to work with Ed25519 as there is only one point format which is always
normed to avoid complications when chaining operations such as `scalarmult`s.


### Range signatures

Bulletproof generation and verification is implemented, however the device can handle maximum 2 batched outputs
in the bulletproof due to high memory requirements (more on that in [monero-doc]). If number of outputs is larger
than 2 the offloading to host is required. In such case, the bulletproofs are first computed at the host and sent to
Trezor for verification.

Bulletproof implementation is covered by unit tests, the proofs in unittest were generated by the Monero C++
implementation.





[trezor-crypto]: https://github.com/trezor/trezor-crypto
[trezor-core]: https://github.com/trezor/trezor-core
[monero-doc]: https://github.com/ph4r05/monero-trezor-doc
[monero-serialize]: https://github.com/ph4r05/monero-serialize
