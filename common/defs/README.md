# Coin and FIDO Definitions

This directory hosts JSON definitions of recognized coins, tokens, and FIDO/U2F apps.

## FIDO

The [`fido/`](fido) subdirectory contains definitons of apps whose logos and
names are shown on Trezor T screen for FIDO/U2F authentication.

Each app must have a single JSON file in the `fido/` subdirectory. Every app must have
its `label` set to the user-recognizable application name. The `u2f` field is a list of
U2F origin hashes, and the `webauthn` field is a list of FIDO2/WebAuthn hostnames for
the app. At least one must be present.

Each app can have an icon. If present, it must be a 128x128 pixels RGBA PNG of the same
name as the corresponding JSON name. If the app does not have an icon, it must instead
have a field `no_icon` set to `true` in the JSON.

## Coins

We currently recognize five categories of coins.

#### `bitcoin`

The [`bitcoin/`](bitcoin) subdirectory contains definitions for Bitcoin and altcoins
based on Bitcoin code.

Each Bitcoin-like coin must have a single JSON file in the `bitcoin/` subdirectory,
and a corresponding PNG image with the same name. The PNG must be 96x96 pixels and
the picture must be a circle suitable for displaying on Trezor T.

Testnet is considered a separate coin, so it must have its own JSON and icon.

We will not support coins that have `address_type` 0, i.e., same as Bitcoin.

#### `eth` and `erc20`

Definitions for Ethereum chains (networks) and tokens (erc20) are split in two parts:

1. built-in definitions - some of the chain and token definitions are built into the firmware
   image. List of built-in chains is stored in [`ethereum/networks.json`](ethereum/networks.json)
   and tokens in [`ethereum/tokens.json`](ethereum/tokens.json).
2. external definitions - dynamically generated from multiple sources. Whole process is
   described in separate
   [document](https://docs.trezor.io/trezor-firmware/common/ethereum-definitions.html).

We generally do not accept updates to the built-in definitions. Instead, make sure your
network or token is included in the external definitions. A good place to start is the
[`ethereum-lists` GitHub organization](https://gitub.com/ethereum-lists): add your token
to the [tokens](https://github.com/ethereum-lists/tokens) repository, or your EVM chain to the
[chains](https://github.com/ethereum-lists/chains) repository.

#### `nem`

The file [`nem/nem_mosaics.json`](nem/nem_mosaics.json) describes NEM mosaics.

#### `misc`

Supported coins that are not derived from Bitcoin, Ethereum or NEM are currently grouped
and listed in separate file [`misc/misc.json`](misc/misc.json). Each coin must also have
an icon in `misc/<short>.png`, where `short` is lowercased `shortcut` field from the JSON.

### Keys

Throughout the system, coins are identified by a _key_ - a colon-separated string
generated from the coin's type and shortcut:

* for Bitcoin-likes, key is `bitcoin:<shortcut>`
* for Ethereum networks, key is `eth:<shortcut>:<chain_id>`
* for ERC20 tokens, key is `erc20:<chain_symbol>:<token_shortcut>`
* for NEM mosaic, key is `nem:<shortcut>`
* for others, key is `misc:<shortcut>`

If a token shortcut has a suffix, such as `CAT (BlockCat)`, the whole thing is part
of the key (so the key is `erc20:eth:CAT (BlockCat)`).

Duplicate keys are not allowed and coins that would result in duplicate keys cannot be
added to the dataset.


# Support Information

We keep track of support status of each built-in coin over our devices. That is `T1B1`
for Trezor One, `T2T1` for Trezor T, `T2B1` and `T3B1` for Trezor Safe 3 (both models
should have identical entries, except for minimum versions which are higher on `T3B1`),
`T3T1` for Trezor Safe 5.

This information is stored in [`support.json`](support.json).
External contributors should not touch this file unless asked to.

Each coin on each device can be in one of four support states:

* **supported** explicitly: coin's key is listed in the device's `supported`
  dictionary. If it's a Trezor device, it contains the firmware version from which
  it is supported. For connect and suite, the value is simply `true`.
* **unsupported** explicitly: coin's key is listed in the device's `unsupported`
  dictionary. The value is a string with reason for not supporting.
  For connect and suite, if the key is not listed at all, it is also considered unsupported.
  ERC20 tokens detected as duplicates are also considered unsupported.
* **unknown**: coin's key is not listed at all.

_Supported_ coins are used in code generation (i.e., included in built firmware).
_Unsupported_ and _unknown_ coins are excluded from code generation.

You can edit `support.json` manually, but it is usually better to use the `support.py` tool.
See [tools docs](../tools) for details.
