# XRP

MAINTAINER = Tomas Susanka <tomas.susanka@satoshilabs.com>

AUTHOR = Tomas Susanka <tomas.susanka@satoshilabs.com>

REVIEWER = Jan Pochyla <jan.pochyla@satoshilabs.com>

CONTRIBUTORS = Towo Labs AB <hello@towo.io>

-----

## Documentation

Developers documentation on the XRP Ledger can be found at [xrpl.org](https://xrpl.org/).

## Transactions

Trezor support all 18 XRP Ledger [transaction types](https://xrpl.org/transaction-types.html) and all [common fields](https://xrpl.org/transaction-common-fields.html). You can use your Trezor to store both XRP and assets issued on the XRP Ledger such as USD, SOLO and stocks. All supported transaction types:

* **AccountSet**, set options on an account.
* **AccountDelete**, delete an account.
* **CheckCancel**, cancel a check.
* **CheckCash**, redeem a check.
* **CheckCreate**, create a check.
* **DepositPreauth**, preauthorize deposits from certain counterparties.
* **EscrowCancel**, reclaim escrowed XRP.
* **EscrowCreate**, create an escrowed XRP payment.
* **EscrowFinish**, deliver escrowed XRP to the recipient.
* **OfferCancel**, withdraw a currency-exchange order.
* **OfferCreate**, submit an order to exchange currency.
* **Payment**, send funds from one account to another.
* **PaymentChannelClaim**, claim money from a payment channel.
* **PaymentChannelCreate**, open a new payment channel.
* **PaymentChannelFund**, add more XRP to a payment channel.
* **SetRegularKey**, add, remove or modify an account's regular key pair.
* **SignerListSet**, add, remove or modify an account's multi-signing list.
* **TrustSet**, add or modify a trust line.

#### Interfaces

The Trezor [command line client](https://github.com/trezor/trezor-firmware/tree/master/python) or [connect](https://github.com/trezor/connect) can be used to send unsigned transactions to a Trezor. After confirming the transaction on the device, a serialized signed transaction will be returned, ready to be submitted to the XRP Ledger. If you need to serialize or deserialize transactions in your application, refer to [ripple-binary-codec](https://github.com/ripple/ripple-binary-codec).

#### Signing
The XRP Ledger supports three methods of authorizing transactions. You can have any combination of authorization methods enabled for the XRP Ledger accounts on your Trezor, including the master key pair, a [regular key](https://xrpl.org/cryptographic-keys.html#regular-key-pair) pair or [multi-signing list](https://xrpl.org/multi-signing.html).

Trezor devices sign transactions using ECDSA and the secp256k1 curve, same as in Bitcoin. The XRP Ledger also supports signing using ed25519, but this is currently unsupported by Trezor.

#### Submitting

To submit signed transactions to the XRP Ledger you can use [ripple-lib](https://github.com/ripple/ripple-lib) and its [submit](https://xrpl.org/rippleapi-reference.html#submit) method. For production use, please see [reliable transaction submission](https://xrpl.org/reliable-transaction-submission.html). After submitting a transaction, you can look up its status by using ripple-lib or a transaction explorer:

* [XRPL Explorer](https://livenet.xrpl.org/)
* [Bithomp](https://bithomp.com/explorer/) 
* [XRP Scan](https://xrpscan.com/)

## Tests

Unit tests are located in the [/core/tests](/core/tests) directory and device tests are in the [/tests/device_tests](/tests/device_tests) directory.