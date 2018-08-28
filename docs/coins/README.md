# List of used BIP-44 derivation paths

| coin           | curve          | getPublicKey   | getAddress       | sign             | derivation      | note         |
|----------------|----------------|----------------|------------------|------------------|-----------------|--------------|
| Bitcoin        | secp256k       | 44'/0'/a'      | 44'/0'/a'/y/i    | 44'/0'/a'/y/i    | [BIP-32](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki) | [7](#BitcoinDiagram) |
| Ethereum       | secp256k       | 44'/60'/a'{/0}<sup>[1](#ETHPublicKey)</sup> | 44'/60'/a'/0/i   | 44'/60'/a'/0/i   | BIP-32            |  |
| Ripple         | secp256k       |       -        | 44'/144'/a'/0/i  | 44'/144'/a'/0/i  | BIP-32            | [2](#Ripple) |
| Stellar        | ed25519        |       -        | 44'/148'/a'      | 44'/148'/a'      | [SLIP-0010](https://github.com/satoshilabs/slips/blob/master/slip-0010.md) | [3](#Stellar) |
| Cardano        | ed25519        | 44'/1815'/a'   | 44'/1815'/a'/0/i | 44'/1815'/a'/0/i | [Cardano's own](https://cardanolaunch.com/assets/Ed25519_BIP.pdf)<sup>[4](#Cardano)</sup> |  |
| Lisk           | ed25519        | 44'/134'/a'    | 44'/134'/a'      | 44'/134'/a'      | SLIP-0010         |      |
| NEM            | ed25519        |       -        | 44'/43'/a'/0'/0' | 44'/43'/a'/0'/0' | SLIP-0010         | [5](#NEM)  |
| Monero         | ed25519        | 44'/128'/a'<sup>[6](#Monero)</sup> | 44'/128'/a'      | 44'/128'/a'      | SLIP-0010         | |

## Notes

1. <a name="ETHPublicKey"></a> This should probably be `44'/60'/a'`, but unfortunately MyEtherWallet sends `44'/60'/a'/0`. So for backwards compatibility we allow both options. trezor.wallet.io sends `44'/60'/a'/0` for MEW compatibility.

2. <a name="Ripple"></a> Although Ripple does not have the concept of change, it uses secp256k and has normal derivation defined. For interoperability reasons we use `44'/144'/a'/0/i`.

3. <a name="Stellar"></a> Defined by Stellar themselves in their [SEP-0005](https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md).

4. <a name="Cardano"></a> Which allows normal derivation on ed25519.

5. <a name="NEM"></a> NEM's path should probably be `44'/60'/a'`, but due to historical reasons this is set to `44'/60'/a'/0'/0'`.

6. <a name="Monero"></a> Actually it is GetWatchKey for Monero.

7. <a name="BitcoinDiagram"></a> With some exceptions. The following diagram shows a path should be validated for Bitcoin-like coins:

![bitcoin-path-check](bitcoin-path-check.svg)
