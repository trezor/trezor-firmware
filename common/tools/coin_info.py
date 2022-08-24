#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import os
import re
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Dict  # for python38 support, must be used in type aliases
from typing import List  # for python38 support, must be used in type aliases
from typing import Any, Callable, Iterable, Iterator, cast

from typing_extensions import (  # for python37 support, is not present in typing there
    Literal,
    TypedDict,
)

try:
    import requests
except ImportError:
    requests = None

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

if os.environ.get("DEFS_DIR"):
    DEFS_DIR = Path(os.environ.get("DEFS_DIR")).resolve()
else:
    DEFS_DIR = ROOT / "defs"


class SupportItemBool(TypedDict):
    supported: dict[str, bool]
    unsupported: dict[str, bool]


class SupportItemVersion(TypedDict):
    supported: dict[str, str]
    unsupported: dict[str, str]


class SupportData(TypedDict):
    connect: SupportItemBool
    suite: SupportItemBool
    trezor1: SupportItemVersion
    trezor2: SupportItemVersion


class SupportInfoItem(TypedDict):
    connect: bool
    suite: bool
    trezor1: Literal[False] | str
    trezor2: Literal[False] | str


SupportInfo = Dict[str, SupportInfoItem]

WalletItems = Dict[str, str]
WalletInfo = Dict[str, WalletItems]


class Coin(TypedDict):
    # Necessary fields for BTC - from BTC_CHECKS
    coin_name: str
    coin_shortcut: str
    coin_label: str
    website: str
    github: str
    maintainer: str
    curve_name: str
    address_type: int
    address_type_p2sh: int
    maxfee_kb: int
    minfee_kb: int
    hash_genesis_block: str
    xprv_magic: int
    xpub_magic: int
    xpub_magic_segwit_p2sh: int
    xpub_magic_segwit_native: int
    slip44: int
    segwit: bool
    decred: bool
    fork_id: int
    force_bip143: bool
    default_fee_b: dict[str, int]
    dust_limit: int
    blocktime_seconds: int
    signed_message_header: str
    uri_prefix: str
    min_address_length: int
    max_address_length: int
    bech32_prefix: str
    cashaddr_prefix: str

    # Other fields optionally coming from JSON
    links: dict[str, str]
    wallet: WalletItems
    curve: str
    decimals: int

    # Mandatory fields added later in coin.update()
    name: str
    shortcut: str
    key: str
    icon: str

    # Special ETH fields
    chain: str
    chain_id: str
    rskip60: bool
    url: str

    # Special erc20 fields
    symbol: str
    address: str
    address_bytes: bytes
    dup_key_nontoken: bool
    deprecation: dict[str, str]

    # Special NEM fields
    ticker: str

    # Fields that are being created
    unsupported: bool
    duplicate: bool
    support: SupportInfoItem

    # Backend-oriented fields
    blockchain_link: dict[str, Any]
    blockbook: list[str]
    bitcore: list[str]


Coins = List[Coin]
CoinBuckets = Dict[str, Coins]


class FidoApp(TypedDict):
    name: str
    webauthn: list[str]
    u2f: list[dict[str, str]]
    use_sign_count: bool
    use_self_attestation: bool
    no_icon: bool

    key: str
    icon: str


FidoApps = List[FidoApp]


def load_json(*path: str | Path) -> Any:
    """Convenience function to load a JSON file from DEFS_DIR."""
    if len(path) == 1 and isinstance(path[0], Path):
        file = path[0]
    else:
        file = Path(DEFS_DIR, *path)

    return json.loads(file.read_text(), object_pairs_hook=OrderedDict)


# ====== CoinsInfo ======


class CoinsInfo(Dict[str, Coins]):
    """Collection of information about all known kinds of coins.

    It contains the following lists:
    `bitcoin` for btc-like coins,
    `eth` for ethereum networks,
    `erc20` for ERC20 tokens,
    `nem` for NEM mosaics,
    `misc` for other networks.

    Accessible as a dict or by attribute: `info["misc"] == info.misc`
    """

    def as_list(self) -> Coins:
        return sum(self.values(), [])

    def as_dict(self) -> dict[str, Coin]:
        return {coin["key"]: coin for coin in self.as_list()}

    def __getattr__(self, attr: str) -> Coins:
        if attr in self:
            return self[attr]
        else:
            raise AttributeError(attr)


# ====== coin validation ======


def check_type(
    val: Any,
    types: type | tuple[type, ...],
    nullable: bool = False,
    empty: bool = False,
    regex: str | None = None,
    choice: list[str] | None = None,
) -> None:
    # check nullable
    if val is None:
        if nullable:
            return
        else:
            raise ValueError("Missing required value")

    # check type
    if not isinstance(val, types):
        raise TypeError(f"Wrong type (expected: {types})")

    # check empty
    if isinstance(val, (list, dict)) and not empty and not val:
        raise ValueError("Empty collection")
    if isinstance(val, str) and not empty and not val:
        raise ValueError("Empty string")

    # check regex
    if regex is not None:
        if types is not str:
            raise TypeError("Wrong type for regex check")
        assert isinstance(val, str)
        if not re.search(regex, val):
            raise ValueError(f"Value does not match regex {regex}")

    # check choice
    if choice is not None and val not in choice:
        choice_str = ", ".join(choice)
        raise ValueError(f"Value not allowed, use one of: {choice_str}")


def check_key(
    key: str, types: type | tuple[type, ...], optional: bool = False, **kwargs: Any
) -> Callable[[Coin], None]:
    def do_check(coin: Coin) -> None:
        if key not in coin:
            if optional:
                return
            else:
                raise KeyError(f"{key}: Missing key")
        try:
            check_type(coin[key], types, **kwargs)
        except Exception as e:
            raise ValueError(f"{key}: {e}") from e

    return do_check


BTC_CHECKS = [
    check_key("coin_name", str, regex=r"^[A-Z]"),
    check_key("coin_shortcut", str, regex=r"^t?[A-Z]{3,}$"),
    check_key("coin_label", str, regex=r"^x?[A-Z]"),
    check_key("website", str, regex=r"^https://.*[^/]$"),
    check_key("github", str, regex=r"^https://git(hu|la)b.com/.*[^/]$"),
    check_key("maintainer", str),
    check_key(
        "curve_name",
        str,
        choice=[
            "secp256k1",
            "secp256k1_decred",
            "secp256k1_groestl",
            "secp256k1_smart",
        ],
    ),
    check_key("address_type", int),
    check_key("address_type_p2sh", int),
    check_key("maxfee_kb", int),
    check_key("minfee_kb", int),
    check_key("hash_genesis_block", str, regex=r"^[0-9a-f]{64}$"),
    check_key("xprv_magic", int),
    check_key("xpub_magic", int),
    check_key("xpub_magic_segwit_p2sh", int, nullable=True),
    check_key("xpub_magic_segwit_native", int, nullable=True),
    check_key("slip44", int),
    check_key("segwit", bool),
    check_key("decred", bool),
    check_key("fork_id", int, nullable=True),
    check_key("force_bip143", bool),
    check_key("default_fee_b", dict),
    check_key("dust_limit", int),
    check_key("blocktime_seconds", int),
    check_key("signed_message_header", str),
    check_key("uri_prefix", str, regex=r"^[a-z-\.\+]+$"),
    check_key("min_address_length", int),
    check_key("max_address_length", int),
    check_key("bech32_prefix", str, regex=r"^[a-z-\.\+]+$", nullable=True),
    check_key("cashaddr_prefix", str, regex=r"^[a-z-\.\+]+$", nullable=True),
]


def validate_btc(coin: Coin) -> list[str]:
    errors: list[str] = []
    for check in BTC_CHECKS:
        try:
            check(coin)
        except Exception as e:
            errors.append(str(e))

    magics: list[int] = [
        coin[k]
        for k in (
            "xprv_magic",
            "xpub_magic",
            "xpub_magic_segwit_p2sh",
            "xpub_magic_segwit_native",
        )
        if coin[k] is not None
    ]
    # each of those must be unique
    # therefore length of list == length of set of unique values
    if len(magics) != len(set(magics)):
        errors.append("XPUB/XPRV magic numbers must be unique")

    if coin["address_type"] == coin["address_type_p2sh"]:
        errors.append("address_type must be distinct from address_type_p2sh")

    if not coin["maxfee_kb"] >= coin["minfee_kb"]:
        errors.append("max fee must not be smaller than min fee")

    if not coin["max_address_length"] >= coin["min_address_length"]:
        errors.append("max address length must not be smaller than min address length")

    if "testnet" in coin["coin_name"].lower() and coin["slip44"] != 1:
        errors.append("testnet coins must use slip44 coin type 1")

    if coin["segwit"]:
        if coin["bech32_prefix"] is None:
            errors.append("bech32_prefix must be defined for segwit-enabled coin")
        if coin["xpub_magic_segwit_p2sh"] is None:
            errors.append(
                "xpub_magic_segwit_p2sh must be defined for segwit-enabled coin"
            )
    else:
        if coin["bech32_prefix"] is not None:
            errors.append("bech32_prefix must not be defined for segwit-disabled coin")
        if coin["xpub_magic_segwit_p2sh"] is not None:
            errors.append(
                "xpub_magic_segwit_p2sh must not be defined for segwit-disabled coin"
            )

    return errors


# ======= Coin json loaders =======


def _load_btc_coins() -> Coins:
    """Load btc-like coins from `bitcoin/*.json`"""
    coins: Coins = []
    for file in DEFS_DIR.glob("bitcoin/*.json"):
        coin: Coin = load_json(file)
        coin.update(
            name=coin["coin_label"],
            shortcut=coin["coin_shortcut"],
            key=f"bitcoin:{coin['coin_shortcut']}",
            icon=str(file.with_suffix(".png")),
        )
        coins.append(coin)

    return coins


def _load_ethereum_networks() -> Coins:
    """Load ethereum networks from `ethereum/networks.json`"""
    chains_path = DEFS_DIR / "ethereum" / "chains" / "_data" / "chains"
    networks: Coins = []
    for chain in sorted(
        chains_path.glob("eip155-*.json"),
        key=lambda x: int(x.stem.replace("eip155-", "")),
    ):
        chain_data = load_json(chain)
        shortcut = chain_data["nativeCurrency"]["symbol"]
        name = chain_data["name"]
        title = chain_data.get("title", "")
        is_testnet = "testnet" in name.lower() or "testnet" in title.lower()
        if is_testnet:
            slip44 = 1
        else:
            slip44 = chain_data.get("slip44", 60)

        if is_testnet and not shortcut.lower().startswith("t"):
            shortcut = "t" + shortcut

        rskip60 = shortcut in ("RBTC", "TRBTC")

        # strip out bullcrap in network naming
        if "mainnet" in name.lower():
            name = re.sub(r" mainnet.*$", "", name, flags=re.IGNORECASE)

        network = dict(
            chain=chain_data["shortName"],
            chain_id=chain_data["chainId"],
            slip44=slip44,
            shortcut=shortcut,
            name=name,
            rskip60=rskip60,
            url=chain_data["infoURL"],
            key=f"eth:{shortcut}",
        )
        networks.append(cast(Coin, network))

    return networks


def _load_erc20_tokens() -> Coins:
    """Load ERC20 tokens from `ethereum/tokens` submodule."""
    networks = _load_ethereum_networks()
    tokens: Coins = []
    for network in networks:
        chain = network["chain"]

        chain_path = DEFS_DIR / "ethereum" / "tokens" / "tokens" / chain
        for file in sorted(chain_path.glob("*.json")):
            token: Coin = load_json(file)
            token.update(
                chain=chain,
                chain_id=network["chain_id"],
                address_bytes=bytes.fromhex(token["address"][2:]),
                shortcut=token["symbol"],
                key=f"erc20:{chain}:{token['symbol']}",
            )
            tokens.append(token)

    return tokens


def _load_nem_mosaics() -> Coins:
    """Loads NEM mosaics from `nem/nem_mosaics.json`"""
    mosaics: Coins = load_json("nem/nem_mosaics.json")
    for mosaic in mosaics:
        shortcut = mosaic["ticker"].strip()
        mosaic.update(shortcut=shortcut, key=f"nem:{shortcut}")
    return mosaics


def _load_misc() -> Coins:
    """Loads miscellaneous networks from `misc/misc.json`"""
    others: Coins = load_json("misc/misc.json")
    for other in others:
        other.update(key=f"misc:{other['shortcut']}")
    return others


def _load_fido_apps() -> FidoApps:
    """Load FIDO apps from `fido/*.json`"""
    apps: FidoApps = []
    for file in sorted(DEFS_DIR.glob("fido/*.json")):
        app_name = file.stem.lower()
        app = load_json(file)
        app.setdefault("use_sign_count", None)
        app.setdefault("use_self_attestation", None)
        app.setdefault("u2f", [])
        app.setdefault("webauthn", [])

        icon_file = file.with_suffix(".png")
        if not icon_file.exists():
            icon_path = None
        else:
            icon_path = str(icon_file)

        app.update(key=app_name, icon=icon_path)
        apps.append(app)

    return apps


# ====== support info ======

RELEASES_URL = "https://data.trezor.io/firmware/{}/releases.json"
MISSING_SUPPORT_MEANS_NO = ("connect", "suite")
VERSIONED_SUPPORT_INFO = ("trezor1", "trezor2")


def get_support_data() -> SupportData:
    """Get raw support data from `support.json`."""
    return load_json("support.json")


def latest_releases() -> dict[str, Any]:
    """Get latest released firmware versions for Trezor 1 and 2"""
    if not requests:
        raise RuntimeError("requests library is required for getting release info")

    latest: dict[str, Any] = {}
    for v in ("1", "2"):
        releases = requests.get(RELEASES_URL.format(v)).json()
        latest["trezor" + v] = max(tuple(r["version"]) for r in releases)
    return latest


def is_token(coin: Coin) -> bool:
    return coin["key"].startswith("erc20:")


def support_info_single(support_data: SupportData, coin: Coin) -> SupportInfoItem:
    """Extract a support dict from `support.json` data.

    Returns a dict of support values for each "device", i.e., `support.json`
    top-level key.

    The support value for each device is determined in order of priority:
    * if the coin has an entry in `unsupported`, its support is `False`
    * if the coin has an entry in `supported` its support is that entry
      (usually a version string, or `True` for connect/suite)
    * if the coin doesn't have an entry, its support status is `None`
    """
    support_info_item = {}
    key = coin["key"]
    for device, values in support_data.items():
        assert isinstance(values, dict)
        if key in values["unsupported"]:
            support_value: Any = False
        elif key in values["supported"]:
            support_value = values["supported"][key]
        elif device in MISSING_SUPPORT_MEANS_NO:
            support_value = False
        else:
            support_value = None
        support_info_item[device] = support_value
    return cast(SupportInfoItem, support_info_item)


def support_info(coins: Iterable[Coin] | CoinsInfo | dict[str, Coin]) -> SupportInfo:
    """Generate Trezor support information.

    Takes a collection of coins and generates a support-info entry for each.
    The support-info is a dict with keys based on `support.json` keys.
    These are usually: "trezor1", "trezor2", "connect" and "suite".

    The `coins` argument can be a `CoinsInfo` object, a list or a dict of
    coin items.

    Support information is taken from `support.json`.
    """
    if isinstance(coins, CoinsInfo):
        coins = coins.as_list()
    elif isinstance(coins, dict):
        coins = coins.values()

    support_data = get_support_data()
    support: SupportInfo = {}
    for coin in coins:
        support[coin["key"]] = support_info_single(support_data, coin)

    return support


# ====== wallet info ======

WALLET_SUITE = {"Trezor Suite": "https://suite.trezor.io"}
WALLET_NEM = {"Nano Wallet": "https://nemplatform.com/wallets/#desktop"}
WALLETS_ETH_3RDPARTY = {
    "MyEtherWallet": "https://www.myetherwallet.com",
    "MyCrypto": "https://mycrypto.com",
}


def get_wallet_data() -> WalletInfo:
    """Get wallet data from `wallets.json`."""
    return load_json("wallets.json")


def _suite_support(coin: Coin, support: SupportInfoItem) -> bool:
    """Check the "suite" support property.
    If set, check that at least one of the backends run on trezor.io.
    If yes, assume we support the coin in our wallet.
    Otherwise it's probably working with a custom backend, which means don't
    link to our wallet.
    """
    if not support["suite"]:
        return False
    return any(".trezor.io" in url for url in coin["blockbook"])


def wallet_info_single(
    support_data: SupportInfo,
    eth_networks_support_data: SupportInfo,
    wallet_data: WalletInfo,
    coin: Coin,
) -> WalletItems:
    """Adds together a dict of all wallets for a coin."""
    wallets: WalletItems = {}

    key = coin["key"]

    # Add wallets from the coin itself
    # (usually not there, only for the `misc` category)
    wallets.update(coin.get("wallet", {}))

    # Each coin category has different further logic
    if key.startswith("bitcoin:"):
        if _suite_support(coin, support_data[key]):
            wallets.update(WALLET_SUITE)
    elif key.startswith("eth:"):
        if support_data[key]["suite"]:
            wallets.update(WALLET_SUITE)
        else:
            wallets.update(WALLETS_ETH_3RDPARTY)
    elif key.startswith("erc20:"):
        if eth_networks_support_data[coin["chain"]]["suite"]:
            wallets.update(WALLET_SUITE)
        else:
            wallets.update(WALLETS_ETH_3RDPARTY)
    elif key.startswith("nem:"):
        wallets.update(WALLET_NEM)
    elif key.startswith("misc:"):
        pass  # no special logic here
    else:
        raise ValueError(f"Unknown coin category: {key}")

    # Add wallets from `wallets.json`
    # This must come last as it offers the ability to override existing wallets
    # (for example with `"MyEtherWallet": null` we delete the MyEtherWallet from the coin)
    wallets.update(wallet_data.get(key, {}))

    # Removing potentially disabled wallets from the last step
    wallets = {name: url for name, url in wallets.items() if url}

    return wallets


def wallet_info(coins: Iterable[Coin] | CoinsInfo | dict[str, Coin]) -> WalletInfo:
    """Generate Trezor wallet information.

    Takes a collection of coins and generates a WalletItems entry for each.
    The WalletItems is a dict with keys being the names of the wallets and
    values being the URLs to those - same format as in `wallets.json`.

    The `coins` argument can be a `CoinsInfo` object, a list or a dict of
    coin items.

    Wallet information is taken from `wallets.json`.
    """
    if isinstance(coins, CoinsInfo):
        coins = coins.as_list()
    elif isinstance(coins, dict):
        coins = coins.values()

    support_data = support_info(coins)
    wallet_data = get_wallet_data()

    # Needed to find out suitable wallets for all the erc20 coins (Suite vs 3rd party)
    eth_networks = [coin for coin in coins if coin["key"].startswith("eth:")]
    eth_networks_support_data = {
        n["chain"]: support_data[n["key"]] for n in eth_networks
    }

    wallet: WalletInfo = {}
    for coin in coins:
        wallet[coin["key"]] = wallet_info_single(
            support_data, eth_networks_support_data, wallet_data, coin
        )

    return wallet


# ====== data cleanup functions ======


def _ensure_mandatory_values(coins: Coins) -> None:
    """Checks that every coin has the mandatory fields: name, shortcut, key"""
    for coin in coins:
        if not all(coin.get(k) for k in ("name", "shortcut", "key")):
            raise ValueError(coin)


def symbol_from_shortcut(shortcut: str) -> tuple[str, str]:
    symsplit = shortcut.split(" ", maxsplit=1)
    return symsplit[0], symsplit[1] if len(symsplit) > 1 else ""


def mark_duplicate_shortcuts(coins: Coins) -> CoinBuckets:
    """Finds coins with identical symbols and sets their `duplicate` field.

    "Symbol" here means the first part of `shortcut` (separated by space),
    so, e.g., "BTL (Battle)" and "BTL (Bitlle)" have the same symbol "BTL".

    The result of this function is a dictionary of _buckets_, each of which is
    indexed by the duplicated symbol, or `_override`. The `_override` bucket will
    contain all coins that are set to `true` in `duplicity_overrides.json`.

    Each coin in every bucket will have its "duplicate" property set to True, unless
    it's explicitly marked as `false` in `duplicity_overrides.json`.
    """
    dup_symbols: CoinBuckets = defaultdict(list)

    for coin in coins:
        symbol, _ = symbol_from_shortcut(coin["shortcut"].lower())
        dup_symbols[symbol].append(coin)

    dup_symbols = {k: v for k, v in dup_symbols.items() if len(v) > 1}
    # mark duplicate symbols
    for values in dup_symbols.values():
        for coin in values:
            coin["duplicate"] = True

    return dup_symbols


def apply_duplicity_overrides(coins: Coins) -> Coins:
    overrides = load_json("duplicity_overrides.json")
    override_bucket: Coins = []
    for coin in coins:
        override_value = overrides.get(coin["key"])
        if override_value is True:
            override_bucket.append(coin)
        if override_value is not None:
            coin["duplicate"] = override_value

    return override_bucket


def deduplicate_erc20(buckets: CoinBuckets, networks: Coins) -> None:
    """Apply further processing to ERC20 duplicate buckets.

    This function works on results of `mark_duplicate_shortcuts`.

    Buckets that contain at least one non-token are ignored - symbol collisions
    with non-tokens always apply.

    Otherwise the following rules are applied:

    1. If _all tokens_ in the bucket have shortcuts with distinct suffixes, e.g.,
    `CAT (BitClave)` and `CAT (Blockcat)`, the bucket is cleared - all are considered
    non-duplicate.

    (If even one token in the bucket _does not_ have a distinct suffix, e.g.,
    `MIT` and `MIT (Mychatcoin)`, this rule does not apply and ALL tokens in the bucket
    are still considered duplicate.)

    2. If there is only one "main" token in the bucket, the bucket is cleared.
    That means that all other tokens must either be on testnets, or they must be marked
    as deprecated, with a deprecation pointing to the "main" token.
    """

    testnet_networks = {n["chain"] for n in networks if n["slip44"] == 1}

    def clear_bucket(bucket: Coins) -> None:
        # allow all coins, except those that are explicitly marked through overrides
        for coin in bucket:
            coin["duplicate"] = False

    for bucket in buckets.values():
        # Only check buckets that contain purely ERC20 tokens. Collision with
        # a non-token is always forbidden.
        if not all(is_token(c) for c in bucket):
            continue

        splits = (symbol_from_shortcut(coin["shortcut"]) for coin in bucket)
        suffixes = {suffix for _, suffix in splits}
        # if 1. all suffixes are distinct and 2. none of them are empty
        if len(suffixes) == len(bucket) and all(suffixes):
            clear_bucket(bucket)
            continue

        # protected categories:
        testnets = [coin for coin in bucket if coin["chain"] in testnet_networks]
        deprecated_by_same = [
            coin
            for coin in bucket
            if "deprecation" in coin
            and any(
                other["address"] == coin["deprecation"]["new_address"]
                for other in bucket
            )
        ]
        remaining = [
            coin
            for coin in bucket
            if coin not in testnets and coin not in deprecated_by_same
        ]
        if len(remaining) <= 1:
            for coin in deprecated_by_same:
                deprecated_symbol = "[deprecated] " + coin["symbol"]
                coin["shortcut"] = coin["symbol"] = deprecated_symbol
                coin["key"] += ":deprecated"
            clear_bucket(bucket)


def deduplicate_keys(all_coins: Coins) -> None:
    dups: CoinBuckets = defaultdict(list)
    for coin in all_coins:
        dups[coin["key"]].append(coin)

    for coins in dups.values():
        if len(coins) <= 1:
            continue
        for i, coin in enumerate(coins):
            if is_token(coin):
                coin["key"] += ":" + coin["address"][2:6].lower()  # first 4 hex chars
            elif "chain_id" in coin:
                coin["key"] += ":" + str(coin["chain_id"])
            else:
                coin["key"] += f":{i}"
                coin["dup_key_nontoken"] = True


def fill_blockchain_links(all_coins: CoinsInfo) -> None:
    blockchain_links = load_json("blockchain_link.json")
    for coins in all_coins.values():
        for coin in coins:
            link = blockchain_links.get(coin["key"])
            coin["blockchain_link"] = link
            if link and link["type"] == "blockbook":
                coin["blockbook"] = link["url"]
            else:
                coin["blockbook"] = []


def _btc_sort_key(coin: Coin) -> str:
    if coin["name"] in ("Bitcoin", "Testnet", "Regtest"):
        return "000000" + coin["name"]
    else:
        return coin["name"]


def collect_coin_info() -> CoinsInfo:
    """Returns all definition as dict organized by coin type.
    `coins` for btc-like coins,
    `eth` for ethereum networks,
    `erc20` for ERC20 tokens,
    `nem` for NEM mosaics,
    `misc` for other networks.
    """
    all_coins = CoinsInfo(
        bitcoin=_load_btc_coins(),
        eth=_load_ethereum_networks(),
        erc20=_load_erc20_tokens(),
        nem=_load_nem_mosaics(),
        misc=_load_misc(),
    )

    for coins in all_coins.values():
        _ensure_mandatory_values(coins)

    fill_blockchain_links(all_coins)

    return all_coins


def sort_coin_infos(all_coins: CoinsInfo) -> None:
    for k, coins in all_coins.items():
        if k == "bitcoin":
            coins.sort(key=_btc_sort_key)
        elif k == "nem":
            # do not sort nem
            pass
        elif k == "eth":
            # sort ethereum networks by chain_id
            coins.sort(key=lambda c: c["chain_id"])
        else:
            coins.sort(key=lambda c: c["key"].upper())


def coin_info_with_duplicates() -> tuple[CoinsInfo, CoinBuckets]:
    """Collects coin info, detects duplicates but does not remove them.

    Returns the CoinsInfo object and duplicate buckets.
    """
    all_coins = collect_coin_info()
    coin_list = all_coins.as_list()
    # generate duplicity buckets based on shortcuts
    buckets = mark_duplicate_shortcuts(all_coins.as_list())
    # apply further processing to ERC20 tokens, generate deprecations etc.
    deduplicate_erc20(buckets, all_coins.eth)
    # ensure the whole list has unique keys (taking into account changes from deduplicate_erc20)
    deduplicate_keys(coin_list)
    # apply duplicity overrides
    buckets["_override"] = apply_duplicity_overrides(coin_list)
    sort_coin_infos(all_coins)

    return all_coins, buckets


def coin_info() -> CoinsInfo:
    """Collects coin info, fills out support info and returns the result.

    Does not auto-delete duplicates. This should now be based on support info.
    """
    all_coins, _ = coin_info_with_duplicates()
    # all_coins["erc20"] = [
    #     coin for coin in all_coins["erc20"] if not coin.get("duplicate")
    # ]
    return all_coins


def fido_info() -> FidoApps:
    """Returns info about known FIDO/U2F apps."""
    return _load_fido_apps()


def search(coins: CoinsInfo | Coins, keyword: str) -> Iterator[Any]:
    kwl = keyword.lower()
    if isinstance(coins, CoinsInfo):
        coins = coins.as_list()

    for coin in coins:
        key = coin["key"].lower()
        name = coin["name"].lower()
        shortcut = coin["shortcut"].lower()
        symbol, suffix = symbol_from_shortcut(shortcut)
        if (
            kwl == key
            or kwl in name
            or kwl == shortcut
            or kwl == symbol
            or kwl in suffix
        ):
            yield coin
