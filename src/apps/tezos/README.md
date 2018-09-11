# Tezos

Tezos documentation can be found [here](http://tezos.gitlab.io).

## Operations

Tezos allows users to use multiple curves for private key derivation, but we support
only `ed25519` (because it is the most used one) where addresses are prefixed with `tz1`,
public keys with `edpk` and signatures with `edsig`. Other curves might be added later on.

Trezor supports basic Tezos user operations - reveal, transaction, origination, delegation.
When the account creates first operation in lifetime, reveal has to be bundled
with this operation to reveal account's public key.

#### Operations Explorer

[TzScan](http://tzscan.io)

## Tests

Unit tests are located in the `tests` directory, device tests are in the python-trezor repository.
