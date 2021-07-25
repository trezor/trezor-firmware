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

## Important notes

Cardano requires a custom `seed.py` file and `Keychain` class. This is because the original Cardano derivation schemes don't separate seed generation from key tree derivation and also because we need to support both Byron (44') and Shelley (1852') purposes. More on this can be found [here](https://github.com/satoshilabs/slips/blob/master/slip-0023.md) and [here](https://github.com/input-output-hk/implementation-decisions/blob/e2d1bed5e617f0907bc5e12cf1c3f3302a4a7c42/text/1852-hd-chimeric.md).

Cardano uses extended public keys. This also means that the transaction signature is built using the `ed25519.sign_ext` function.

## Protocol magic vs. Network id

Protocol magic is used to identify the network on the protocol level. Each network (mainnet, testnet, testnet 2, ...) has its own protocol magic. It's a 4 byte number. Network Id is a more compact version of the protocol magic - it's only 4 bits. It is used in addresses to determine, whether they belong to a testnet or any of the (possibly in the future existing) mainnets. Network Id 0 is reserved for all the testnets that might ever exist and the remaining 15 values are used for mainnets.
_Current mainnet protocol magic:_ 764824073
_Current mainnet network id:_ 1

## Key types

In Shelley two types of keys are used. Payment key and staking key. Payment keys are derived from _m/1852'/1815'/x/[0,1]/y_ paths and are used for holding/transferring funds. Staking keys are derived from _m/1852'/1815'/x/2/0_ paths, thus there is only one staking key per account. They are used for staking operations - certificates, withdrawals. Shelley addresses are built from the combination of hashes of these keys.

## Addresses

Since the Shelley era Cardano supports multiple address types. Information about address types added in Shelley can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/460ee17d22cacb3ac4d90536ebe90500a356a1c9/shelley/chain-and-ledger/shelley-spec-ledger-test/cddl-files/shelley.cddl#L68). In short, all Shelley address types contain a header, which is 1 byte long. The header is built as: `((address_type << 4) | networkId)`. Byron address has an address type of `0b1000` but never contains the network id. Instead, protocol magic is included in the address in a different way (more about that [here](https://github.com/input-output-hk/cardano-wallet/wiki/About-Address-Format---Byron)).

#### Address encoding (Base58 vs. Bech32)

In Shelley, address encoding has been switched from Base58 to Bech32. However, Byron addresses still need to be encoded as Base58. Other address types use Bech32. Thus both formats need to be supported.

#### Byron address

Legacy address used mainly during the Byron era, but still supported in Shelley. Has no staking rights. More about address format can be found [here](https://github.com/input-output-hk/cardano-wallet/wiki/About-Address-Format---Byron).
**Example:**
Mainnet: `Ae2tdPwUPEZCanmBz5g2GEwFqKTKpNJcGYPKfDxoNeKZ8bRHr8366kseiK2`
Testnet: `2657WMsDfac7BteXkJq5Jzdog4h47fPbkwUM49isuWbYAr2cFRHa3rURP236h9PBe`

#### Base address

Introduced in Shelley:
`[header] + [payment_key_hash] + [staking_key_hash]`
Base address can have staking rights (as it contains a staking key hash), but the staking key has to be registered on the blockchain first. Funds can be received even without the staking key being registered though. It is also possible to own the funds (payment key) but to use a different staking key to build the address. This would transfer the staking rights to the owner of the staking key. This can be useful for staking your funds for a charity.
**Example:**
Mainnet: `addr1q8v42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wnrqua2vw243tmjfjt0h5wsru6appuz8c0pfd75ur7myyeqsx9990`
Testnet: `addr_test1qrv42wjda8r6mpfj40d36znlgfdcqp7jtj03ah8skh6u8wnrqua2vw243tmjfjt0h5wsru6appuz8c0pfd75ur7myyeqnsc9fs`

#### Pointer address

Introduced in Shelley:
`[header] + [payment_key_hash] + [certificate_pointer]`
Certificate pointer is a pointer `(block, transaction, certificate)` to the staking key registration certificate on the blockchain. It replaces `staking_key_hash` from base address, but serves the same purpose. Thus pointer address is pretty much the same as base address in function, but is much shorter (~35B vs 57B) thanks to the certificate pointer.
**Example:**
Mainnet: `addr1gxq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92spqgpsl97q83`
Testnet: `addr_test1gzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z925ph3wczvf2ag2x9t`

#### Enterprise address

Introduced in Shelley:
`[header] + [payment_key_hash]`
Entreprise address has no staking rights. This is useful for example for exchanges which contain a lot of funds and thus would control too much stake.
**Example:**
Mainnet: `addr1vxq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92su77c6m`
Testnet: `addr_test1vzq0nckg3ekgzuqg7w5p9mvgnd9ym28qh5grlph8xd2z92s8k2y47`

#### Reward address

Introduced in Shelley:
`[header] + [staking_key_hash]`
Staking rewards are gathered on this address after stake registration and delegation. They can then be withdrawn by a transaction with `withdrawals` filled in. All of the rewards have to be taken out at once.
**Example:**
Mainnet: `stake1uyfz49rtntfa9h0s98f6s28sg69weemgjhc4e8hm66d5yacalmqha`
Testnet: `stake_test1uqfz49rtntfa9h0s98f6s28sg69weemgjhc4e8hm66d5yac643znq`


## Transactions

Transactions don't have a distinct type. Every transaction may transfer funds, post a certificate, withdraw funds or do all at once (to a point).

_Unfortunately we are aware of the fact that currently at most ~14 inputs are supported per transaction. This should be resolved when the cardano app is updated to support transaction streaming._

#### Witnesses

Transactions need a witness (signature) for each input, withdrawal and some certificates. A witness for each key is included only once in a transaction. The signature is built using the `ed25519.sign_ext` function. There are significant differences between Byron and Shelley witnesses - although we need to support both, because a transaction may have Byron inputs.

_Shelley witnesses_:
They only need to contain the public key (not the extended public key) and the signature. Nothing else is needed to verify the signature, although the signing happens with an extended private key.

_Byron witnesses_:
In order to be able to properly verify them, Byron witnesses need to contain the public key, signature, chain code and address attributes (which are empty on mainnet or contain the protocol magic on testnet).

More on witness structure can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/097890495cbb0e8b62106bcd090a5721c3f4b36f/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L219).

#### Multi Asset support

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

#### Certificates

Certificates are posted to the blockchain via transactions and they mark a certain action, thus there are multiple certificate types:
* stake key registration certificate
* stake key de-registration certificate
* delegation certificate

And these three which are not supported by Trezor at the moment:
* stake pool registration certificate
* stake pool retirement certificate
* operational key certificate

Stake key de-registration and delegation certificates both need to be witnessed by the corresponding staking key.

You can read more on certificates in the [delegation design spec](https://hydra.iohk.io/build/2006688/download/1/delegation_design_spec.pdf#subsection.3.4).
Info about their structure can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/097890495cbb0e8b62106bcd090a5721c3f4b36f/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L102).

#### Withdrawals

Withdrawals are posted to the blockchain via transactions and they are used to withdraw rewards from reward accounts. When withdrawing funds, the transaction needs to be witnessed by the corresponding staking key.

You can read more on withdrawals in the [delegation design spec](https://hydra.iohk.io/build/2006688/download/1/delegation_design_spec.pdf) (there is not a dedicated section to withdrawals, simply search for 'withdrawal').

#### Auxiliary data

_Auxiliary data have replaced metadata in the Cardano Mary era_

Each transaction may contain auxiliary data. Auxiliary data format can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/57c27d168b8d4288534ce74e77c1df33870e756a/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl#L212).

Auxiliary data can be sent to Trezor as a blob or as an object with parameters. The blob will be included in the transaction as is.

The only object currently supported is Catalyst voting key registration. To be in compliance with the CDDL and other Cardano tools, Catalyst voting key registration object is being wrapped in a tuple and an empty tuple follows it. The empty tuple represents `auxiliary_scripts` which are not yet supported on Trezor and are thus always empty. Byron addresses are not supported as Catalyst reward addresses.

[Catalyst Registration Transaction Metadata Format](https://github.com/cardano-foundation/CIPs/blob/749f22eccd78e05fcdc4552c49639bb3bbd0a458/CIP-0015/CIP-0015.md)

#### Transaction Explorer

[Cardano explorer](https://explorer.cardano.org/en.html).

#### Submitting a transaction

You can use a combination of [cardano-node](https://github.com/input-output-hk/cardano-node) and cardano-cli (part of the cardano-node repo) to submit a transaction.

## Serialization format
Cardano uses [CBOR](https://www.rfc-editor.org/info/rfc7049) as a serialization format. [Here](https://github.com/input-output-hk/cardano-ledger-specs/blob/097890495cbb0e8b62106bcd090a5721c3f4b36f/shelley-ma/shelley-ma-test/cddl-files/shelley-ma.cddl) is the [CDDL](https://tools.ietf.org/html/rfc8610) specification for after Multi Asset support has been added.

#### Raw transaction example
```
83a800818258203b40265111d8bb3c3c608d95b3a0bf83461ace32d79336579a1939b3aad1c0b700018282583901eb0baa5e570cffbe2934db29df0b6a3d7c0430ee65d4c3a7ab2fefb91bc428e4720702ebd5dab4fb175324c192dc9bb76cc5da956e3c8dff821904d2a1581c95a292ffee938be03e9bae5657982a74e9014eb4960108c9e23a5b39a14874652474436f696e1910e18258390180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b427719115c02182a030a048182008200581c122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b427705a1581de1122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b42771903e80758205410cfffe33d9da8b3ab789068f12e0464fad13f586f92d8c8c2fcac68c1a9c00814a100828258205d010cf16fdeff40955633d6c565f3844a288a24967cf6b76acbeb271b4f13c158406478ca1a1d1bab66688a19e983fbff9e7f9120f0035d9663ae8eb917cf01ce1c4b47834d06f41cf0c7c5218be0224ab1d88de97b20572d6fdc3cb1e40b662300825820bc65be1b0b9d7531778a1317c2aa6de936963c3f9ac7d5ee9e9eda25e0c97c5e584023ddaf5c9f5c9a22fd646f1c1c5a3f1a84c3a43d90d2211e919450c35df53bcded772e0badb33a898c03f3c227765bc21e678d85b716e0055ca9d89274d6660e82a219ef64a4015820cdea4080a301fdfda7a6b9c8b5283273f51af5f34ae587e05c5492f90a2ae54f025820bc65be1b0b9d7531778a1317c2aa6de936963c3f9ac7d5ee9e9eda25e0c97c5e0358390180f9e2c88e6c817008f3a812ed889b4a4da8e0bd103f86e7335422aa122a946b9ad3d2ddf029d3a828f0468aece76895f15c9efbd69b4277041a015d76c419ef65a101584017ed3f6a8ef2d0f1212e3aa49766fcf22b087c6cfa5cf247ecbc6c27069d7c17f189f2ca0acf6f1d54e1999e12fc37ac695c693982df96430896b54e0bcff10780
```

#### The same transactions with structure description
```
# transaction
# array(3)
[
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
   8: 20
 },
  # witnesses
  # map(1)
 {
   # verifying key witnesses [[vkey -> signature]]
   # uint(0), array(2)
   0: [
       # array(2), bytes(32), bytes(64)
       [h'5D0...', h'647...'],
       # array(2), bytes(32), bytes(64)
       [h'BC6...', h'23D...']
   ]
 },
 # auxiliary data - catalyst voting key registration
 # array(2)
 [
   # map(2)
   {
     # uint(61284), map(4), uint(1), bytes(32), uint(2), bytes(32), uint(3), bytes(57), uint(4), uint(22902468)
     61284: {
       1: h'CDE...',
       2: h'BC6...',
       3: h'018...',
       4: 22902468
     },
     # uint(61285), map(1), bytes(64)
     61285: {
       1:h'17E...'
     }
   },
   # array(0)
   []
 ]
]
```
