# BIP-44 derivation paths

Each coin uses [BIP-44](https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki) derivation path scheme. If the coin is UTXO-based the path should have all five parts, precisely as defined in [BIP-32](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki). If it is account-based we follow Stellar's [SEP-0005](https://github.com/stellar/stellar-protocol/blob/master/ecosystem/sep-0005.md) - paths have only three parts `44'/c'/a'`. Unfortunately, lot of exceptions occur due to compatibility reasons.

## List of used derivation paths

| coin           | curve          | getPublicKey   | getAddress       | sign tx          | derivation      | note         |
|----------------|----------------|----------------|------------------|------------------|-----------------|--------------|
| Bitcoin        | secp256k       | 44'/c'/a'      | 44'/c'/a'/y/i    | 44'/c'/a'/y/i    | BIP-32          | [1](#Bitcoin) |
| Ethereum       | secp256k       | 44'/60'/0'     | 44'/60'/0'/0/i   | 44'/60'/0'/0/i   | BIP-32          | [2](#Ethereum)|
| Ripple         | secp256k       |       -        | 44'/144'/a'/0/0  | 44'/144'/a'/0/0  | BIP-32          | [3](#Ripple) |
| Cardano        | ed25519        | 44'/1815'/a'   | 44'/1815'/a'/{0,1}/i | 44'/1815'/a'/{0,1}/i | [Cardano's own](https://cardanolaunch.com/assets/Ed25519_BIP.pdf)<sup>[4](#Cardano)</sup> |  |
| Stellar        | ed25519        |       -        | 44'/148'/a'      | 44'/148'/a'      | SLIP-0010       |  |
| Lisk           | ed25519        | 44'/134'/a'    | 44'/134'/a'      | 44'/134'/a'      | SLIP-0010       |  |
| NEM            | ed25519        |       -        | 44'/43'/a'       | 44'/43'/a'       | SLIP-0010       | [5](#NEM)  |
| Monero         | ed25519        | 44'/128'/a'<sup>[6](#Monero)</sup> | 44'/128'/a'      | 44'/128'/a'      | SLIP-0010         | |
| Tezos          | ed25519<sup>[7](#Tezos)</sup> | 44'/1729'/a' | 44'/1729'/a'      | 44'/1729'/a'      | SLIP-0010         | |

Paths that do not conform to this table are allowed, but user needs to confirm a warning on Trezor. For getPublicKey we do not check if the path is followed by other non-hardened items (anyone can derive those anyway). This is beneficial  for Ethereum and its MEW compatibility, which sends `44'/60'/0'/0` for getPublicKey.

## Notes

1. <a name="Bitcoin"></a> For Bitcoin and its derivatives it is a little bit more complicated. `p` is decided based on the following table:

    | p   | type         | input script type  |
    |-----|--------------|--------------------|
    | 44 | legacy        | SPENDADDRESS       |
    | 48 | multisig      | SPENDMULTISIG      |
    | 49 | p2sh segwit   | SPENDP2SHWITNESS   |
    | 84 | native segwit | SPENDWITNESS       |

Other `p` are disallowed. `c` has to be equal to the coin's [slip44 id](https://github.com/satoshilabs/slips/blob/master/slip-0044.md) as for every coin. `y` needs to be 0 or 1.

2. <a name="Ethereum"></a> We believe this should be `44'/60'/a'`, because Ethereum is account-based, rather than UTXO-based. Unfortunately, lot of Ethereum tools (MEW, Metamask) do not use such scheme and set `a = 0` and then iterate the address index `i`. Therefore for compatibility reasons we use the same scheme: `44'/60'/0'/0/i` and only the `i` is being iterated.

3. <a name="Ripple"></a> Similar to Ethereum this should be `44'/144'/a'`. But for compatibility with other HW vendors we use `44'/144'/a'/0/0`.

4. <a name="Cardano"></a> Which allows non-hardened derivation on ed25519.

5. <a name="NEM"></a> NEM's path should be `44'/60'/a'` as per SEP-0005, but we allow `44'/60'/a'/0'/0'` as well for compatibility reasons with NanoWallet.

6. <a name="Monero"></a> Actually it is GetWatchKey for Monero.

7. <a name="Tezos"></a> Tezos supports multiple curves, but Trezor currently supports ed25519 only.

Sign message paths are validated in the same way as the sign tx paths are.

## Allowed values

For GetPublicKey `a` needs in the interval of \[0, 20]. For GetAddress and signing the longer five-items paths need to have `a` also in range of \[0, 20] and `i` in \[0, 1000000]. If only three-items paths are used (Stellar and Lisk for example), `a` is allowed to be in \[0, 1000000] (because there is no address index `i`).
