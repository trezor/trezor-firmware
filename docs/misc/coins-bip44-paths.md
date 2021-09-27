# BIP-44 derivation paths

Each coin uses [BIP-44] derivation path scheme. If the coin is UTXO-based the path
should have all five parts, precisely as defined in [BIP-32]. If it is account-based we
follow Stellar's [SEP-0005] - paths have only three parts `44'/c'/a'`. Unfortunately,
lot of exceptions occur due to compatibility reasons.

Keys are derived according to [SLIP-10], which is a superset of the BIP-32 derivation
algorithm, extended to work on other curves.

[bip-44]: https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
[bip-32]: https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki
[sep-0005]: https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md
[slip-10]: https://github.com/satoshilabs/slips/blob/master/slip-0010.md

## List of used derivation paths

| coin     | curve     | path               | public node | note           |
| -------- | --------- | ------------------ | ----------- | -------------- |
| Bitcoin  | secp256k1 | `44'/c'/a'/y/i`    | yes         | [1](#Bitcoin)  |
| Ethereum | secp256k1 | `44'/c'/0'/0/a`    | yes         | [2](#Ethereum) |
| Ripple   | secp256k1 | `44'/144'/a'/0/0`  |             | [3](#Ripple)   |
| EOS      | secp256k1 | `44'/194'/a'/0/0`  |             | [3](#Ripple)   |
| Binance  | secp256k1 | `44'/714'/a'/0/0`  |             | [3](#Ripple)   |
| Tron     | secp256k1 | TODO               |             | TODO           |
| Ontology | nist256p1 | TODO               |             | TODO           |
| Cardano  | ed25519   | `44'/1815'/a'/y/i` | yes         | [4](#Cardano)  |
| Stellar  | ed25519   | `44'/148'/a'`      |             |                |
| NEM      | ed25519   | `44'/43'/a'`       |             | [5](#NEM)      |
| Monero   | ed25519   | `44'/128'/a'`      |             |                |
| Tezos    | ed25519   | `44'/1729'/a'`     |             | [6](#Tezos)    |

`c` stands for the [SLIP-44 id] of the currency, when multiple currencies are handled
by the same code. `a` is an account number, `y` is change address indicator (must be
0 or 1), and `i` is address index.

[slip-44 id]: https://github.com/satoshilabs/slips/blob/master/slip-0044.md

Paths that do not conform to this table are allowed, but user needs to confirm a warning
on Trezor.

### Public nodes

Some currencies allow exporting a _public node_, which lets the client derive all
non-hardened paths below it. In that case, the conforming path is equal to the
hardened prefix.

I.e., for Bitcoin's path `44'/c'/a'/y/i`, the allowed public node path is `44'/c'/a'`.

Trezor does not check if the path is followed by other non-hardened items (anyone can
derive those anyway). This is beneficial for Ethereum and its MEW compatibility, which
sends `44'/60'/0'/0` for getPublicKey.

### Notes

1. <a name="Bitcoin"></a> For Bitcoin and its derivatives it is a little bit more
   complicated. `p` is decided based on the following table:

   | p   | type            | input script type |
   | --- | --------------- | ----------------- |
   | 44  | legacy          | SPENDADDRESS      |
   | 48  | legacy multisig | SPENDMULTISIG     |
   | 49  | p2sh segwit     | SPENDP2SHWITNESS  |
   | 84  | native segwit   | SPENDWITNESS      |

   Other `p` are disallowed.

2. <a name="Ethereum"></a> We believe this should be `44'/c'/a'`, because Ethereum is
   account-based, rather than UTXO-based. Unfortunately, lot of Ethereum tools (MEW,
   Metamask) do not use such scheme and set `a = 0` and then iterate the address index
   `i`. Therefore for compatibility reasons we use the same scheme.

3. <a name="Ripple"></a> Similar to Ethereum this should be `44'/c'/a'`. But for
   compatibility with other HW vendors we use `44'/c'/a'/0/0`.

4. <a name="Cardano"></a> Cardano has a [custom derivation] algorithm that allows
   non-hardened derivation on ed25519.

[custom derivation]: https://cardanolaunch.com/assets/Ed25519_BIP.pdf

5. <a name="NEM"></a> NEM's path should be `44'/43'/a'` as per SEP-0005, but we allow
   `44'/43'/a'/0'/0'` as well for compatibility reasons with NanoWallet.

6. <a name="Tezos"></a> Tezos supports multiple curves, but Trezor currently supports
   ed25519 only.

Sign message paths are validated in the same way as the sign tx paths are.

## Allowed values

For UTXO-based currencies, account number `a` needs to be in the interval \[0, 20]
and address index `i` in the interval \[0, 1 000 000].

For account-based currencies (i.e., those that do not use address indexes), account
number `a` needs to be in the interval \[0, 1 000 000]
