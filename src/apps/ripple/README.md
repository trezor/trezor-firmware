# Ripple

MAINTAINER = Tomas Susanka <tomas.susanka@satoshilabs.com>

AUTHOR = Tomas Susanka <tomas.susanka@satoshilabs.com>

REVIEWER = Jan Pochyla <jan.pochyla@satoshilabs.com>

-----

## Documentation

Ripple's documentation can be found [here](https://developers.ripple.com/) and on the deprecated [wiki](https://wiki.ripple.com).

## Transactions

Ripple has different transaction types, see the [documentation](https://developers.ripple.com/transaction-formats.html) for the structure and the list of all transaction types. The concept is somewhat similar to Stellar. However, Stellar's transaction is composed of operations, whereas in Ripple each transaction is simply of some transaction type.

We do not support transaction types other than the [Payment](https://developers.ripple.com/payment.html) transaction, which represents the simple "A pays to B" scenario. Other transaction types might be added later on.

We currently sign transactions using ECDSA and the secp256k1 curve same as in Bitcoin. Ripple also supports ed25519, which is currently not supported by Trezor, although the implementation would be quite straightforward.

Non-XRP currencies are not supported. Float and negative amounts are not supported.

#### Transactions Explorer

[Bithomp](https://bithomp.com/) seems to work fine.

#### Submitting a transaction

You can use [ripple-lib](https://github.com/ripple/ripple-lib) and its [submit](https://github.com/ripple/ripple-lib/blob/develop/docs/index.md#submit) method to publish a transaction into the Ripple network. Python-trezor returns a serialized signed transaction, which is exactly what you provide as an argument into the submit function.

## Serialization format

Ripple uses its own [serialization format](https://wiki.ripple.com/Binary_Format). In a simple case, the first nibble of a first byte denotes the type and the second nibble the field. The actual data follow.

Our implementation in `serialize.py` is a simplification of the protocol tailored for the support of the Payment type exclusively.

## Tests

Unit tests are located in the `tests` directory, device tests are in the python-trezor repository.
