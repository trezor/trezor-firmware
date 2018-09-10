# Coin Definitions

We currently recognize five categories of coins.

#### `bitcoin`

The [`bitcoin/`](bitcoin) subdirectory contains definitions for Bitcoin and altcoins
based on Bitcoin code. The `coins/` subdirectory is a compatibility link to `bitcoin`.

Each Bitcoin-like coin must have a single JSON file in the `bitcoin/` subdirectory,
and a corresponding PNG image with the same name. The PNG must be 96x96 pixels and
the picture must be a circle suitable for displaying on Trezor T.

Testnet is considered a separate coin, so it must have its own JSON and icon.

We will not support coins that have `address_type` 0, i.e., same as Bitcoin.

#### `eth`

The file [`ethereum/networks.json`](ethereum/networks.json) has a list of descriptions
of Ethereum networks. Each network must also have a PNG icon in `ethereum/<chain>.png`
file.

#### `erc20`

`ethereum/tokens` is a submodule linking to [Ethereum Lists](https://github.com/ethereum-lists/tokens)
project with descriptions of ERC20 tokens. If you want to add or update a token
definition in Trezor, you need to get your change to the `tokens` repository first.

Trezor will only support tokens that have a unique symbol.

#### `nem`

The file [`nem/nem_mosaics.json`](nem/nem_mosaics.json) describes NEM mosaics.

#### `misc`

Supported coins that are not derived from Bitcoin, Ethereum or NEM are currently grouped
and listed in separate file [`misc/misc.json`](misc/misc.json). Each coin must also have
an icon in `misc/<short>.png`, where `short` is lowercased `shortcut` field from the JSON.

## Keys

Throughout the system, coins are identified by a _key_ - a colon-separated string
generated from the coin's type and shortcut:

* for Bitcoin-likes, key is `bitcoin:XYZ`
* for Ethereum networks, key is `eth:XYZ`
* for ERC20 tokens, key is `erc20:<chain>:XYZ`
* for NEM mosaic, key is `nem:XYZ`
* for others, key is `misc:XYZ`

If a token shortcut has a suffix, such as `CAT (BlockCat)`, the whole thing is part
of the key (so the key is `erc20:eth:CAT (BlockCat)`).

Sometimes coins end up with duplicate symbols, which in case of ERC20 tokens leads to
key collisions. We do not allow duplicate symbols in the data, so this doesn't affect
everyday use (see below). However, for validation purposes, it is sometimes useful
to work with unfiltered data that includes the duplicates. In such cases, keys are
deduplicated by adding a counter at end, e.g.: `erc20:eth:SMT:0`, `erc20:eth:SMT:1`.
Note that the suffix _is not stable_, so these coins can't be reliably uniquely identified.

## Duplicate Detection

**Duplicate symbols are not allowed** in our data. Tokens that have symbol collisions
are removed from the data set before processing. The duplicate status is mentioned
in `support.json` (see below), but it is impossible to override from there.

Duplicate detection works as follows:

1. a _symbol_ is split off from the shortcut string. E.g., for `CAT (BlockCat)`, symbol
   is just `CAT`. It is compared, case-insensitive, with other coins (so `WIC` and `WiC`
   are considered the same symbol), and identical symbols are put into a _bucket_.
2. if _all_ coins in the bucket also have a suffix (`CAT (BlockCat)` and `CAT (BitClave)`),
   they are _not_ considered duplicate.
3. if _any_ coin in the bucket does _not_ have a suffix (`MIT` and `MIT (Mychatcoin)`),
   all coins in the bucket are considered duplicate.
4. Duplicate tokens (coins from the `erc20` group) are automatically removed from data.
   Duplicate non-tokens are marked but not removed. For instance, `bitcoin:FTC` (Feathercoin)
   and `erc20:eth:FTC` (FTC) are duplicate, and `erc20:eth:FTC` is removed.
5. If two non-tokens collide with each other, it is an error that fails the CI build.

The file [`duplicity_overrides.json`](duplicity_overrides.json) can override detection
results: keys set to `true` are considered duplicate (in a separate bucket), keys set
to `false` are considered non-duplicate even if auto-detected. This is useful for
whitelisting a supported token explicitly, or blacklisting things that the detection
can't match (for instance "Battle" and "Bitlle" have suffixes, but they are too similar).

External contributors should not make changes to `duplicity_overrides.json`, unless
asked to.

You can use `./tools/cointool.py check -d all` to inspect duplicate detection in detail.


# Coins Details

The file [`coins_details.json`](coins_details.json) is a list of all known coins
with support status, market cap information and relevant links. This is the source
file for https://trezor.io/coins.

You should never make changes to `coins_details.json` directly. Use `./tools/coins_details.py`
to regenerate it from known data.

If you need to change information in this file, modify the source information instead -
one of the JSON files in the groups listed above, support info in `support.json`, or
make a pull request to the tokens repository.

If this is not viable for some reason, or if there is no source information (such as
links to third-party wallets), you can also edit [`coins_details.override.json`](coins_details.override.json).
External contributors should not touch this file unless asked to.


# Support Information

We keep track of support status of each coin over our devices. That is
`trezor1` for Trezor One, `trezor2` for Trezor T, `connect` for [Connect](https://github.com/trezor/connect)
and `webwallet` for [Trezor Wallet](https://wallet.trezor.io/). In further description, the word "device"
applies to Connect and webwallet as well.

This information is stored in [`support.json`](support.json).
External contributors should not touch this file unless asked to.

Each coin on each device can be in one of four support states:

* **supported** explicitly: coin's key is listed in the device's `supported`
  dictionary. If it's a Trezor device, it contains the firmware version from which
  it is supported. For connect and webwallet, the value is simply `true`.
* **unsupported** explicitly: coin's key is listed in the device's `unsupported`
  dictionary. The value is a string with reason for not supporting.  
  For connect and webwallet, if the key is not listed at all, it is also considered unsupported.  
  ERC20 tokens detected as duplicates are also considered unsupported.
* **soon**: coin's key is listed in the device's `supported` dictionary, with
  the value `"soon"`.  
  ERC20 tokens that are not listed at all are also considered `soon`, unless detected
  as duplicates.
* **unknown**: coin's key is not listed at all.

_Supported_ and _soon_ coins are used in code generation (i.e., included in built firmware).
_Unsupported_ and _unknown_ coins are excluded from code generation.

That means that new ERC20 tokens are included as soon as you update the tokens repository.
New coin definitions, on the other hand, are not included until someone sets their
support status to _soon_ (or a version) explicitly.

You can edit `support.json` manually, but it is usually better to use the `support.py` tool.
See [tools docs](../tools) for details.
