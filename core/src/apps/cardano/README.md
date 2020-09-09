# Cardano

MAINTAINER = Gabriel Kerekeš <gabriel.kerekes@vacuumlabs.com>

ORIGINAL AUTHOR = Juraj Muravský <juraj.muravsky@vacuumlabs.com>

SHELLEY UPDATE AUTHOR = Gabriel Kerekeš <gabriel.kerekes@vacuumlabs.com>

REVIEWER = Jan Matejek <jan.matejek@satoshilabs.com>, Tomas Susanka <tomas.susanka@satoshilabs.com>

-----

## Useful links

[Cardano documentation](https://docs.cardano.org/en/latest/) - official documentation.  
[Delegation Design Spec](https://hydra.iohk.io/build/2006688/download/1/delegation_design_spec.pdf) - contains information about delegation (addresses, certificates, withdrawals, ...).  
[Shelley CDDL spec](https://github.com/input-output-hk/cardano-ledger-specs/blob/460ee17d22cacb3ac4d90536ebe90500a356a1c9/shelley/chain-and-ledger/shelley-spec-ledger-test/cddl-files/shelley.cddl).  
[Byron address format](https://github.com/input-output-hk/cardano-wallet/wiki/About-Address-Format---Byron).  
[The Shelley 1852' purpose and staking path](https://github.com/input-output-hk/implementation-decisions/blob/e2d1bed5e617f0907bc5e12cf1c3f3302a4a7c42/text/1852-hd-chimeric.md).  
[cbor.me](http://cbor.me/) - very useful tool for CBOR inspection.

## Important notes

Unfortunately we are aware of the fact that currently at most ~14 inputs are supported per transaction. We suspect this is due to the memory heavy CBOR implementation. This should be fixed in the near future.

Cardano requires a custom `seed.py` file and `Keychain` class. This is because the original Cardano derivation schemes don't separate seed generation from key tree derivation and also because we need to support both Byron (44') and Shelley (1852') purposes. More on this can be found [here](https://github.com/satoshilabs/slips/blob/master/slip-0023.md) and [here](https://github.com/input-output-hk/implementation-decisions/blob/e2d1bed5e617f0907bc5e12cf1c3f3302a4a7c42/text/1852-hd-chimeric.md).

Cardano uses extended public keys. This also means that the transaction signature is built using the `ed25519.sign_ext` function.

## Protocol magic vs. Network id

Protocol magic is used to identify the network on the protocol level. Each network (mainnet, testnet, testnet 2, ...) has its own protocol magic. It's a 4 byte number. Network Id is a more compact version of the protocol magic - it's only 4 bits. It is used in addresses to determine, whether they belong to a testnet or any of the (possibly in the future existing) mainnets. Network Id 0 is reserved for all the testnets that might ever exist and the remaining 15 values are used for mainnets.  
_Current mainnet protocol magic:_ 764824073  
_Current mainnet network id:_ 1

## Key types

In Shelley two types of keys are used. Payment key and staking key. Payment keys are derived from _m/1852'/1815'/x/[0,1]/y_ paths and are used for holding/transfering funds. Staking keys are derived from _m/1852'/1815'/x/2/0_ paths, thus there is only one staking key per account. They are used for staking operations - certificates, withdrawals. Shelley addresses are built from the combination of hashes of these keys.

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

_Unfortunately we are aware of the fact that currently at most ~14 inputs are supported per transaction. We suspect this is due to the memory heavy CBOR implementation. This should be fixed in the near future._

#### Witnesses

Transactions need a witness (signature) for each input, withdrawal and some certificates. A witness for each key is included only once in a transaction. The signature is built using the `ed25519.sign_ext` function. There are significant differences between Byron and Shelley witnesses - although we need to support both, because a transaction may have Byron inputs.

_Shelley witnesses_:  
They only need to contain the public key (not the extended public key) and the signature. Nothing else is needed to verify the signature, although the signing happens with an extended private key.  

_Byron witnesses_:  
In order to be able to properly verify them, Byron witnesses need to contain the public key, signature, chain code and address attributes (which are empty on mainnet or contain the protocol magic on testnet).  

More on witness structure can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/460ee17d22cacb3ac4d90536ebe90500a356a1c9/shelley/chain-and-ledger/shelley-spec-ledger-test/cddl-files/shelley.cddl#L213).

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
Info about their structure can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/460ee17d22cacb3ac4d90536ebe90500a356a1c9/shelley/chain-and-ledger/shelley-spec-ledger-test/cddl-files/shelley.cddl#L102).

#### Withdrawals

Withdrawals are posted to the blockchain via transactions and they are used to withdraw rewards from reward accounts. When withdrawing funds, the transaction needs to be witnessed by the corresponding staking key.

You can read more on withdrawals in the [delegation design spec](https://hydra.iohk.io/build/2006688/download/1/delegation_design_spec.pdf) (there is not a dedicated section to withdrawals, simply search for 'withdrawal').

#### Metadata

Each transaction may contain metadata. Metadata format can be found [here](https://github.com/input-output-hk/cardano-ledger-specs/blob/460ee17d22cacb3ac4d90536ebe90500a356a1c9/shelley/chain-and-ledger/shelley-spec-ledger-test/cddl-files/shelley.cddl#L210). It's basically a CBOR serialized map and can contain numbers, bytes, strings or nested maps/lists.

Due to memory limitations we currently enforce a maximum size of 500 bytes for metadata.

#### Transaction Explorer

[Cardano explorer](https://explorer.cardano.org/en.html).

#### Submitting a transaction

You can use a combination of [cardano-node](https://github.com/input-output-hk/cardano-node) and cardano-cli (part of the cardano-node repo) to submit a transaction.

## Serialization format
Cardano uses [CBOR](https://www.rfc-editor.org/info/rfc7049) as a serialization format. [Here](https://github.com/input-output-hk/cardano-ledger-specs/blob/460ee17d22cacb3ac4d90536ebe90500a356a1c9/shelley/chain-and-ledger/shelley-spec-ledger-test/cddl-files/shelley.cddl) is the [CDDL](https://tools.ietf.org/html/rfc8610) specification for Shelley.


#### Raw transaction example
```
83a600818258200d4a5315236df09f331158cae0f78d3df6cdb952a387bcd160dcb1bd2c708c6b00018182583900667ee84f714720123b92dd159bc306925020c460d464cea40eebc59f6c72a09118a3307789bc6d79e3b2149468f62df586085bcee687ca4d1b00000018fab759cd021a00030d40031a0007a120048182018200581cf228837e81c3baaa1879dbeff94e86fa5eba342aa05cd6d1c3bf23ed05a1581de06c72a09118a3307789bc6d79e3b2149468f62df586085bcee687ca4d1b00000001ad72b9d4a10082825820d198d009e0e482bc940331c3709c7ccdc1decbf0675e7c06380c1da3e129e7265840f62f02511ac77eebdbd87221a3bc9c93cf0971a13107ff41b6ea4ea14d720b361f41ab4994b91022763a10ebe1edf8174ca31ec2c7f56be72759d7e75303b603825820f1cea7b5d7f81e6e7858681634d957117ffe4e78bf9d475dbae9101baddda49858407ac236ad5684d22848a725246e83a043611c8ecebf04864d1b9fae6a33f23684790bc05d44a49b1c0a48df00151acafdcc93c29faf93663c9ed704cefd1a4b0df6
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
   0: [[h'0D4...', 0]],           
 
   # outputs [address, amount]
   # uint(1), array(1), array(2), bytes(57), uint(107285535181)
   1: [[h'006...', 107285535181]],
 
   # fee
   # uint(2), uint(200000)
   2: 200000,                     
 
   # ttl
   # uint(3), uint(500000)
   3: 500000,                     
 
   # certificates [[type, [keyhash/scripthash, keyhash]]]
   # uint(4), array(1), array(2), uint(1), array(2), uint(0), bytes(28)
   4: [[1,[0, h'F22...']]],       
 
   # withdrawal [reward_address: amount]
   # uint(5), map(1), bytes(29), uint(7204944340)
   5: {h'E06...': 7204944340}     
 },       
  # witnesses
  # map(1)
 {                                 
   # verifying key witnesses [[vkey -> signature]]
   # uint(0), array(2)
   0: [       
       # array(2), bytes(32), bytes(64)                   
       [h'D19...', h'F62...'],  
       # array(2), bytes(32), bytes(64) 
       [h'F1C...', h'7AC...']
   ]    
 },
 
 # metadata
 # primitive(22)
 null                             
]
```
