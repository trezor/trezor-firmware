# Purpose48 derivation scheme

Per [BIP-43], the first level of the derivation path is used as a "purpose". The purpose
number is usually selected to match the BIP number: e.g., BIP-49 uses purpose `49'`.

There is no officially proposed **BIP-48** standard. Despite that, a de-facto standard
for the purpose `48'` exists in the wild and is implemented by several HD wallets, most
notably [Electrum]. This standard was never before formally
specified, and this document aims to rectify the situation.

## Motivation

Purpose48 is intended for multisig scenarios. It allows using multiple script types from
a single logical account or root key, while keeping multisig keys separate from
single-sig keys.

## Specification

The following BIP-32 path levels are defined:

```
m / 48' / coin_type' / account' / script_type' / change / address_index
```

Meaning of all fields except `script_type` is defined in [BIP-44]

`script_type` can have the following values:

* `0`: raw [BIP-11] (p2ms) multisig
* `1`: p2sh-wrapped segwit multisig (p2wsh-p2sh)
* `2`: native segwit multisig (p2wsh)

The path derivation is hardened up to and including the `script_type` field.

## Trezor implementation

`script_type` value `0` corresponds to `SPENDMULTISIG`/`PAYTOMULTISIG`.

Value `1` corresponds to `SPENDP2SHWITNESS`/`PAYTOP2SHWITNESS`.

Value `2` corresponds to `SPENDWITNESS`/`PAYTOWITNESS`.

## References

Electrum implementation: https://github.com/spesmilo/electrum/blob/9931df9f254e49eb929723be62af61971b3032c8/electrum/keystore.py#L862-L889

Trezor implementation: TBD

[Electrum]: https://electrum.org/
[BIP-11]: https://github.com/bitcoin/bips/blob/master/bip-0011.mediawiki
[BIP-43]: https://github.com/bitcoin/bips/blob/master/bip-0043.mediawiki
[BIP-44]: https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
