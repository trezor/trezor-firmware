# BIP-44 derivation paths

Each coin uses [BIP-44](https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki) derivation path scheme. If the coin does not support normal derivation  (because the underlying curve does not support it for example) we're using Stellar's  [SEP-0005](https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md). In a nutshell, these paths are derived using [SLIP-0010](https://github.com/satoshilabs/slips/blob/master/slip-0010.md) and have only three-part BIP-44 path `44'/c'/a'`.

## List of used derivation paths

| coin           | curve          | getPublicKey   | getAddress       | sign             | derivation      | note         |
|----------------|----------------|----------------|------------------|------------------|-----------------|--------------|
| Bitcoin        | secp256k       | 44'/0'/a'      | 44'/0'/a'/y/i    | 44'/0'/a'/y/i    | [BIP-32](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki) | [4](#BitcoinDiagram) |
| Ethereum       | secp256k       | 44'/60'/a' | 44'/60'/a'/0/i   | 44'/60'/a'/0/i   | BIP-32            |  |
| Ripple         | secp256k       |       -        | 44'/144'/a'/0/i  | 44'/144'/a'/0/i  | BIP-32            | |
| Stellar        | ed25519        |       -        | 44'/148'/a'      | 44'/148'/a'      | [SLIP-0010](https://github.com/satoshilabs/slips/blob/master/slip-0010.md) |  |
| Cardano        | ed25519        | 44'/1815'/a'   | 44'/1815'/a'/0/i | 44'/1815'/a'/0/i | [Cardano's own](https://cardanolaunch.com/assets/Ed25519_BIP.pdf)<sup>[1](#Cardano)</sup> |  |
| Lisk           | ed25519        | 44'/134'/a'    | 44'/134'/a'      | 44'/134'/a'      | SLIP-0010         |      |
| NEM            | ed25519        |       -        | 44'/43'/a' | 44'/43'/a' | SLIP-0010         | [2](#NEM)  |
| Monero         | ed25519        | 44'/128'/a'<sup>[3](#Monero)</sup> | 44'/128'/a'      | 44'/128'/a'      | SLIP-0010         | |

Paths that do not conform to this table are allowed, but user needs to confirm a warning on Trezor. For getPublicKey we do not check if the path is followed by other non-hardened items (anyone can derive those anyway). This is beneficial  for Ethereum and its MEW compatibility, which sends `44'/60'/a'/0` for getPublicKey.

## Notes

1. <a name="Cardano"></a> Which allows normal derivation on ed25519.

2. <a name="NEM"></a> NEM's path should be `44'/60'/a'` as per SEP-0005, but we allow `44'/60'/a'/0'/0'` as well for compatibility reasons with NanoWallet.

3. <a name="Monero"></a> Actually it is GetWatchKey for Monero.

4. <a name="BitcoinDiagram"></a> It is a bit more complicated for Bitcoin-like coins. The following diagram shows how path should be validated for Bitcoin-like coins:

![bitcoin-path-check](bitcoin-path-check.svg)
