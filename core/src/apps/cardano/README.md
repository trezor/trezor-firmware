# Cardano

MAINTAINER = Rafael Korbaš <rafael.korbas@vacuumlabs.com>

ORIGINAL AUTHOR = Juraj Muravský <juraj.muravsky@vacuumlabs.com>

REVIEWER = Jan Matejek <jan.matejek@satoshilabs.com>, Tomas Susanka <tomas.susanka@satoshilabs.com>

-----

## Useful links

[Cardano documentation](https://docs.cardano.org/en/latest/) - official documentation.

[Cardano developer documentation](https://developers.cardano.org/) - official developer documentation.

[Delegation Design Spec](https://hydra.iohk.io/build/2006688/download/1/delegation_design_spec.pdf) - contains information about delegation (addresses, certificates, withdrawals, ...).

[Multi Asset CDDL spec](https://github.com/input-output-hk/cardano-ledger-specs/blob/097890495cbb0e8b62106bcd090a5721c3f4b36f/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl).

[Byron address format](https://github.com/input-output-hk/cardano-wallet/wiki/About-Address-Format---Byron).

[The Shelley 1852' purpose and staking path](https://github.com/input-output-hk/implementation-decisions/blob/e2d1bed5e617f0907bc5e12cf1c3f3302a4a7c42/text/1852-hd-chimeric.md).

[cbor.me](http://cbor.me/) - very useful tool for CBOR inspection.


## Seed derivation schemes

When using a **BIP-39 seed phrase**, multiple seed derivation schemes are [specified](https://github.com/cardano-foundation/CIPs/blob/master/CIP-0003/README.md):

* `ICARUS`, which is the recommended default.
* `ICARUS_TREZOR`, which differs from Icarus for 24-word seed phrases due to a [historic bug](https://github.com/trezor/trezor-firmware/issues/1387).
  When a seed shorter than 24 words is used, the result is the same as `ICARUS`.
* `LEDGER`, designed and used by the Ledger wallet.

Given the same seed phrase, each of the schemes may produce a different master seed,
and so opens a different wallet.

Icarus (and Icarus-Trezor) scheme processes the seed phrase in a manner incompatible
with BIP-39. A separate derivation step is required when using the Icarus scheme, which
prolongs Trezor's first-response time by 2 seconds, plus additional 2 seconds for
Icarus-Trezor if the seed phrase is 24 words long.

Since firmware version 2.4.3, wallets that require the Cardano-derived seed must specify
`derive_cardano=true` in the `Initialize` call. Otherwise an error will be returned when
performing any Cardano call with an Icarus-like derivation.

Ledger derivation scheme is compatible with BIP-39 and does not require the separate
derivation step. For that reason, it is available even if `derive_cardano=true` was not
specified.

Since firmware version 2.4.3, Trezor requires the caller to specify derivation type in
every Cardano call. In older versions, the Icarus-Trezor derivation is always used.

For compatibility with older firmwares, wallet implementations should default to the
Icarus-Trezor derivation. For compatibility with other wallet vendors, wallets should
make the derivation scheme configurable by user -- or perform a discovery for all three
schemes.

When using **SLIP-39 backup**, the only supported derivation is [SLIP-23](https://github.com/satoshilabs/slips/blob/master/slip-0023.md).
The `derive_cardano=true` parameter is not required, and the value of `derivation_type`
is ignored.

Cardano uses extended public keys. This also means that the transaction signature is built using the `ed25519.sign_ext` function.


## Multiple BIP-32 purposes

Cardano is using the following values for BIP-32 purpose field:

* Byron: 44'
* Shelley: 1852'
* Multi-sig: [1854'](https://cips.cardano.org/cips/cip1854/)
* Minting: [1855'](https://cips.cardano.org/cips/cip1855/)

Details about the purpose identifiers can be found [here](https://github.com/input-output-hk/implementation-decisions/blob/e2d1bed5e617f0907bc5e12cf1c3f3302a4a7c42/text/1852-hd-chimeric.md).


## Protocol magic vs. Network id

Protocol magic is used to identify the network on the protocol level. Each network (mainnet, testnet, testnet 2, ...) has its own protocol magic. It's a 4 byte number. Network Id is a more compact version of the protocol magic - it's only 4 bits. It is used in addresses to determine, whether they belong to a testnet or any of the (possibly in the future existing) mainnets. Network Id 0 is reserved for all the testnets that might ever exist and the remaining 15 values are used for mainnets.

_Current mainnet protocol magic:_ 764824073

_Current mainnet network id:_ 1

## Key types

In Shelley two types of keys are used. Payment key and staking key. Payment keys are derived from _m/1852'/1815'/x/[0,1]/y_ paths and are used for holding/transferring funds. Staking keys are derived from _m/1852'/1815'/x/2/0_ paths, thus there is only one staking key per account. They are used for staking operations - certificates, withdrawals. Shelley addresses are built from the combination of hashes of these keys.

[Multi-sig paths (1854')](https://cips.cardano.org/cips/cip1854/) are used to generate keys which should be used in native scripts and also to sign multi-sig transactions. [Minting paths (1855')](https://cips.cardano.org/cips/cip1855/) are used for creating minting policies and for witnessing minting transactions.

## Addresses

Since the Shelley era Cardano supports multiple address types. Information about address types added in Shelley can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/460ee17d22cacb3ac4d90536ebe90500a356a1c9/shelley/chain-and-ledger/shelley-spec-ledger-test/cddl-files/shelley.cddl#L68). In short, all Shelley address types contain a header, which is 1 byte long. The header is built as: `((address_type << 4) | networkId)`. Byron address has an address type of `0b1000` but never contains the network id. Instead, protocol magic is included in the address in a different way (more about that [here](https://github.com/input-output-hk/cardano-wallet/wiki/About-Address-Format---Byron)).

#### Address encoding (Base58 vs. Bech32)

In Shelley, address encoding has been switched from Base58 to Bech32. However, Byron addresses still need to be encoded as Base58. Other address types use Bech32. Thus both formats need to be supported.

#### Byron address

Legacy address used mainly during the Byron era, but still supported in Shelley. Has no staking rights. More about address format can be found [here](https://github.com/input-output-hk/cardano-wallet/wiki/About-Address-Format---Byron).

**Example:**

Mainnet: `Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2`

Testnet: `2657WMsDfac7BteXkJq5Jzdog4h47fPbkwUM49isuWbYAr2cFRHa3rURP236h9PBe`

#### Credentials

Shelley addresses are built using credentials - `payment_credential` and `staking_credential`. These credentials can either be key hashes or script IDs (hashes). The type of the address (and thus also its header) changes based on which credentials are used. Addresses with key hashes usually represent accounts owned by single users. Addresses with scripts either represent multi-sig (shared) accounts derived from native scripts or they represent Plutus scripts directly.

#### Base address

Introduced in Shelley: `[header] + [payment_credential] + [staking_credential]`

Base address can have staking rights (as it contains a staking credential), but the staking credential has to be registered on the blockchain first. Funds can be received even without the credential being registered though. It is also possible to own the funds (payment credential) but to use a different staking credential to build the address. This would transfer the staking rights to the owner(s) of the staking credential. This can be useful for staking your funds for a charity.

**Example:**

Mainnet: `addr1q8v42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wnrqua2vw243tmjfjt0h5wsru6appuz8c0pfd75ur7myyeqsx9990`

Testnet: `addr_test1qrv42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wnrqua2vw243tmjfjt0h5wsru6appuz8c0pfd75ur7myyeqnsc9fs`

#### Pointer address

Introduced in Shelley: `[header] + [payment_credential] + [certificate_pointer]`

Certificate pointer is a pointer `(block, transaction, certificate)` to the staking credential registration certificate on the blockchain. It replaces `staking_credential` from base address, but serves the same purpose. Thus pointer address is pretty much the same as base address in function, but is much shorter (~35B vs 57B) thanks to the certificate pointer.

**Example:**

Mainnet: `addr1gxq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92spqgpsl97q83`

Testnet: `addr_test1gzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z925ph3wczvf2ag2x9t`

#### Enterprise address

Introduced in Shelley: `[header] + [payment_credential]`

Entreprise address has no staking rights. This is useful for example for exchanges which contain a lot of funds and thus would control too much stake.

**Example:**

Mainnet: `addr1vxq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92su77c6m`

Testnet: `addr_test1vzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92s8k2y47`

#### Reward address

Introduced in Shelley: `[header] + [staking_credential]`

Staking rewards are gathered on this address after stake registration and delegation. They can then be withdrawn by a transaction with `withdrawals` filled in. All of the rewards have to be taken out at once.

**Example:**

Mainnet: `stake1uyfz49rtntfa9h0s98f6s28sg69weemgjhc4e8hm66d5yacalmqha`

Testnet: `stake_test1uqfz49rtntfa9h0s98f6s28sg69weemgjhc4e8hm66d5yac643znq`


## Transactions

Transactions don't have a distinct type. Every transaction may transfer funds, post a certificate, withdraw funds or do all at once (to a point). However, for security purposes we had to limit some combinations of elements e.g. a pool registration transaction being signed by the owner cannot contain any payment witnesses. To identify the transaction type we use a so-called transaction signing mode (`CardanoTxSigningMode`).

### Transaction streaming

In the past transaction parameters have been sent to Trezor as a single, large object which would get processed, and the whole signed and serialized transaction would be returned by Trezor. However, as transactions kept on growing, this approach proved to be very memory inefficient, and the supported transaction size was quite limited (around 2kB).

We have iteratively updated the Cardano implementation so that now the transaction parameters are sent to Trezor one by one and are also processed one-by-one. For example the inputs of a transaction are all sent and processed separately, which means that the number of inputs a single transaction can contain is very large (perhaps even infinite). All lists and maps are processed similarly to the inputs.

Thanks to transaction streaming, it's now possible to sign a transaction with 65 inputs, 40 outputs, another 10 outputs with 12 policies and 10 assets each. The multiasset outputs included in the transaction were all over the 4kB max size given by the protocol. The whole transaction was 62kB (current protocol transaction size limit is 16kB). It could also probably handle much much more, but these tests already took long enough to complete.

### Transaction signing mode

For security and in some cases UX purposes we use transaction signing mode so that we are able to better adjust the policies for a given transaction.

#### Ordinary transaction

An ordinary transaction cannot contain a pool registration certificate. Also multi-sig (1854') witnesses can't be requested.

#### Pool registration as owner

When signing a pool registration transaction as an owner, the transaction cannot contain the following:
- inputs with path, i.e. payment witness requests
- other certificates
- withdrawals
- token minting

Including inputs with a path would cause the transaction to be signed by such a path without letting the user know. Of course, we could let the user know that the transaction is being signed by the user's payment key, however, a pool owner should never be the one paying for the pool registration anyways so such a witness request doesn't make sense.

Just like a pool registration certificate, other certificates and withdrawals are also signed by the user's staking keys. Allowing other certificates and withdrawals to be included in the transaction might thus cause the user to inadvertently sign a delegation certificate or withdrawal along with the pool registration.

#### Multi-sig transaction

Represents a multi-sig transaction using native scripts. Script credentials must be used in certificates and withdrawals when signing a multi-sig transaction. Ordinary (1852') witness requests are not allowed and all the witness requests are shown. Transaction cannot contain a pool registration certificate.

### Single account model

Change outputs, certificates, withdrawals and witness requests (inputs) are allowed to only contain paths from a single account. The single account is determined by the first encountered element containing a path. Byron and Shelley paths with the same account are considered as separate accounts.

### Witnesses

Transactions need a witness (signature) for each input, withdrawal and some certificates. A witness for each key is included only once in a transaction. The signature is built using the `ed25519.sign_ext` function. There are significant differences between Byron and Shelley witnesses - although we need to support both, because a transaction may have Byron inputs.

#### Shelley witnesses

They only need to contain the public key (not the extended public key) and the signature. Nothing else is needed to verify the signature, although the signing happens with an extended private key.

#### Byron witnesses

In order to be able to properly verify them, Byron witnesses need to contain the public key, signature, chain code and address attributes (which are empty on mainnet or contain the protocol magic on testnet).

More on witness structure can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/097890495cbb0e8b62106bcd090a5721c3f4b36f/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L219).

### Multi Asset support

_Multi Asset support has been added in the Cardano Mary era_

_Quote from [developer docs](https://developers.cardano.org/en/development-environments/native-tokens/multi-asset-tokens-explainer/):_
> This feature extends the existing accounting infrastructure defined in the ledger model, which is designed for processing ada-only transactions, to accommodate transactions that simultaneously use a range of assets. These assets include ada and a variety of user-define custom token types.

Transaction outputs may include custom tokens on top of ADA tokens:
```
1: [
 [
  address, [
   ADA_amount, {
    policy_id: {
     asset_name: asset_amount
    }}]]]
```

Please see the transaction below for more details.

#### Token minting/burning

_Token minting/burning support has been added to HW wallets along with multi-sig support_

_Quote from [Cardano docs](https://cardano-ledger.readthedocs.io/en/latest/explanations/policies.html#minting-transactions):_
> To introduce new quantities of new tokens on the ledger (minting) or to remove existing tokens (burning), each transaction features a mint field. The transactions where the mint field is not empty are known as minting transactions. The use of this field needs to be tightly controlled to ensure that the minting and burning of tokens occurs according to the token’s minting policy.

Keys derived from a [minting path (1855')](https://cips.cardano.org/cips/cip1855/) are used to create token minting/burning policies (native scripts). The structure of the mint field can be found in the [CDDL](https://github.com/input-output-hk/cardano-ledger-specs/blob/097890495cbb0e8b62106bcd090a5721c3f4b36f/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L255).

### Certificates

Certificates are posted to the blockchain via transactions and they mark a certain action, thus there are multiple certificate types:
* stake key registration certificate
* stake key de-registration certificate
* delegation certificate
* stake pool registration certificate

And these two which are not supported by Trezor at the moment:
* stake pool retirement certificate
* operational key certificate

Stake key de-registration and delegation certificates both need to be witnessed by the corresponding staking key. A stake pool registration certificate can only be signed on Trezor by a pool owner and the `POOL_REGISTRATION_AS_OWNER` signing mode has to be used. Pool operator support isn't available on Trezor.

You can read more on certificates in the [delegation design spec](https://hydra.iohk.io/build/2006688/download/1/delegation_design_spec.pdf#subsection.3.4).
Info about their structure can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/097890495cbb0e8b62106bcd090a5721c3f4b36f/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L102).

### Withdrawals

Withdrawals are posted to the blockchain via transactions and they are used to withdraw rewards from reward accounts. When withdrawing funds, the transaction needs to be witnessed by the corresponding staking key.

You can read more on withdrawals in the [delegation design spec](https://hydra.iohk.io/build/2006688/download/1/delegation_design_spec.pdf) (there is not a dedicated section to withdrawals, simply search for 'withdrawal').

### Auxiliary data

_Auxiliary data have replaced metadata in the Cardano Mary era_

Each transaction may contain auxiliary data. Auxiliary data format can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/57c27d168b8d4288534ce74e77c1df33870e756a/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L212).

Auxiliary data can be sent to Trezor as a hash or as an object with parameters. The hash will be included in the transaction body as is and will be shown to the user.

The only object currently supported is Catalyst voting key registration. To be in compliance with the CDDL and other Cardano tools, Catalyst voting key registration object is being wrapped in a tuple and an empty tuple follows it. The empty tuple represents `auxiliary_scripts` which are not yet supported on Trezor and are thus always empty. Byron addresses are not supported as Catalyst reward addresses. The Catalyst registration signature is returned in the form of `CardanoTxAuxiliaryDataSupplement` which also contains the auxiliary data hash calculated by Trezor.

[Catalyst Registration Transaction Metadata Format](https://github.com/cardano-foundation/CIPs/blob/749f22eccd78e05fcdc4552c49639bb3bbd0a458/CIP-0015/CIP-0015.md)

### Native scripts

Native scripts are used to describe the multi-sig scheme belonging to a script address or the minting/burning policy of native tokens. Native scripts define what keys need to be used to witness a transaction and what condition needs to be fulfilled in order for that transaction to be valid. See [CDDL](https://github.com/input-output-hk/cardano-ledger-specs/blob/3ff2b08c7e094a3b9035fafb170e0e1da9b75401/eras/alonzo/test-suite/cddl-files/alonzo.cddl#L334) and [CIP-1854](https://cips.cardano.org/cips/cip1854/) for more details.

In order for the user to be able to verify native scripts a `get_native_script_hash` is available on Trezor. This enables the user to verify the contents and the final hash of the script.

#### Transaction Explorer

[Cardano explorer](https://explorer.cardano.org/en.html).

#### Submitting a transaction

You can use a combination of [cardano-node](https://github.com/input-output-hk/cardano-node) and cardano-cli (part of the cardano-node repo) to submit a transaction.

## Serialization format
Cardano uses [CBOR](https://www.rfc-editor.org/info/rfc7049) as a serialization format. [Here](https://github.com/input-output-hk/cardano-ledger-specs/blob/097890495cbb0e8b62106bcd090a5721c3f4b36f/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl) is the [CDDL](https://tools.ietf.org/html/rfc8610) specification for after Multi Asset support has been added.

#### Transaction body example
Input for trezorctl to sign the transaction can be found [here](https://gist.github.com/gabrielKerekes/ad6c168b12ebb43b082df5b92d67e276).

```
a900818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282583901eb0baa5e570cffbe2934db29df0b6a3d7c0430ee65d4c3a7ab2fefb91bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff821904d2a1581c95a292ffee938be03e9bae5657982a74e9014eb4960108c9e23a5b39a14874652474436f696e1910e18258390180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b427719115c02182a030a048182008200581c122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b427705a1581de1122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b42771903e8075820a943e9166f1bb6d767b175384d3bd7d23645170df36fc1861fbf344135d8e120081409a1581c95a292ffee938be03e9bae5657982a74e9014eb4960108c9e23a5b39a24874652474436f696e1a007838624875652474436f696e3a00783861
```

#### The same transaction body with structure description
```
# transaction body
# map(6)
{
  # inputs [id, index]
  # uint(0), array(1), array(2), bytes(32), uint(0)
  0: [[h'3B4...', 0]],

  # outputs [address, [ada_amount, { policy_id => { asset_name => asset_amount }}]]
  # uint(1), array(2)
  1: [
    # multi asset output
    # array(2), bytes(57), uint(1234), map(1), bytes(28), map(1), bytes(8), uint(4321)
    [
      h'01E...', [
        1234, {
          h'95A...': {
            h'74652474436F696E': 4321
          }
        }
      ]
    ],
    # output containing only ADA [address, ada_amount]
    # array(2), bytes(57), uint(4444)
    [h'018...', 4444],
  ]

  # fee
  # uint(2), uint(42)
  2: 42,

  # ttl
  # uint(3), uint(10)
  3: 10,

  # certificates [[type, [keyhash/scripthash, keyhash]]]
  # uint(4), array(1), array(2), uint(0), array(2), uint(0), bytes(28)
  4: [[0,[0, h'122...']]],

  # withdrawal [reward_address: amount]
  # uint(5), map(1), bytes(29), uint(7204944340)
  5: {h'E11...': 1000},

  # auxiliary data hash
  7: h'541...',

  # validity_interval_start
  # uint(8), uint(20)
  8: 20,

  # mint
  # map(2), bytes(8), "te$tCoin", uint(7878754), bytes(8), "ue$tCoin", int(7878753)
  9: {
    h'95A2...': {
      h'7465...': 7878754,
      h'7565...': -7878754
    }
  }
}
```
