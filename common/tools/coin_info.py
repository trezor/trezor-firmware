#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
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
DEFS_DIR = ROOT / "defs"


class SupportItemVersion(TypedDict):
    supported: dict[str, str]
    unsupported: dict[str, str]


SupportData = Dict[str, SupportItemVersion]
SupportInfoItem = Dict[str, Literal[False] | str]
SupportInfo = Dict[str, SupportInfoItem]


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
    curve: str
    decimals: int

    # Mandatory fields added later in coin.update()
    name: str
    shortcut: str
    key: str
    icon: str

    # Special ETH fields
    coingecko_id: str
    chain: str
    chain_id: int
    url: str

    # Special erc20 fields
    symbol: str
    address: str
    address_bytes: bytes
    dup_key_nontoken: bool

    # Special NEM fields
    ticker: str

    # Fields that are being created
    unsupported: bool
    duplicate: bool
    support: SupportInfoItem
    is_testnet: bool

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
    use_compact: bool
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


def get_btc_testnet_status(name: str) -> bool:
    return any((mark in name.lower()) for mark in ("testnet", "regtest"))


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

    if coin["is_testnet"] and coin["slip44"] != 1:
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
            is_testnet=get_btc_testnet_status(coin["coin_label"]),
        )
        coins.append(coin)

    return coins


def _load_builtin_ethereum_networks() -> Coins:
    """Load ethereum networks from `ethereum/networks.json`"""
    chains_data = load_json("ethereum", "networks.json")
    networks: Coins = []
    for chain_data in chains_data:
        chain_data["key"] = f"eth:{chain_data['shortcut']}:{chain_data['chain_id']}"
        # is_testnet is present in the JSON
        networks.append(cast(Coin, chain_data))

    return networks


def _load_builtin_erc20_tokens() -> Coins:
    """Load ERC20 tokens from `ethereum/tokens.json`."""
    tokens_data = load_json("ethereum", "tokens.json")
    all_tokens: Coins = []

    for chain_id_and_chain, tokens in tokens_data.items():
        chain_id, chain = chain_id_and_chain.split(";", maxsplit=1)
        for token in tokens:
            token.update(
                chain=chain,
                chain_id=int(chain_id),
                address=token["address"].lower(),
                address_bytes=bytes.fromhex(token["address"][2:]),
                symbol=token["shortcut"],
                key=f"erc20:{chain}:{token['shortcut']}",
                is_testnet=False,
            )
            all_tokens.append(cast(Coin, token))

    return all_tokens


def _load_nem_mosaics() -> Coins:
    """Loads NEM mosaics from `nem/nem_mosaics.json`"""
    mosaics: Coins = load_json("nem/nem_mosaics.json")
    for mosaic in mosaics:
        shortcut = mosaic["ticker"].strip()
        mosaic.update(
            shortcut=shortcut,
            key=f"nem:{shortcut}",
            is_testnet=False,
        )
    return mosaics


def _load_misc() -> Coins:
    """Loads miscellaneous networks from `misc/misc.json`"""
    others: Coins = load_json("misc/misc.json")
    for other in others:
        other.update(
            key=f"misc:{other['shortcut']}",
            is_testnet=False,
        )
    return others


def _load_fido_apps() -> FidoApps:
    """Load FIDO apps from `fido/*.json`"""
    apps: FidoApps = []
    for file in sorted(DEFS_DIR.glob("fido/*.json")):
        app_name = file.stem.lower()
        app = load_json(file)
        app.setdefault("use_sign_count", None)
        app.setdefault("use_self_attestation", None)
        app.setdefault("use_compact", None)
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


def get_support_data() -> SupportData:
    """Get raw support data from `support.json`."""
    return load_json("support.json")


def get_models() -> list[str]:
    """Get all models from `support.json`."""
    return list(get_support_data().keys())


def latest_releases() -> dict[str, Any]:
    """Get latest released firmware versions for all models"""
    if not requests:
        raise RuntimeError("requests library is required for getting release info")

    latest: dict[str, Any] = {}
    for model in get_models():
        url_model = model.lower()  # need to be e.g. t1b1 for now
        releases = requests.get(RELEASES_URL.format(url_model)).json()
        latest[model] = max(tuple(r["version"]) for r in releases)
    return latest


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
        else:
            support_value = None
        support_info_item[device] = support_value
    return cast(SupportInfoItem, support_info_item)


def support_info(coins: Iterable[Coin] | CoinsInfo | dict[str, Coin]) -> SupportInfo:
    """Generate Trezor support information.

    Takes a collection of coins and generates a support-info entry for each.
    The support-info is a dict with keys based on `support.json` keys.
    These are usually: "T1B1", "T2T1", "T2B1", "connect" and "suite".

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


def find_duplicate_keys(all_coins: Coins) -> None:
    dups: CoinBuckets = defaultdict(list)
    for coin in all_coins:
        dups[coin["key"]].append(coin)

    for coins in dups.values():
        if len(coins) <= 1:
            continue
        coin = coins[0]
        raise ValueError(f"Duplicate key {coin['key']}")


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
        eth=_load_builtin_ethereum_networks(),
        erc20=_load_builtin_erc20_tokens(),
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
    # ensure the whole list has unique keys
    find_duplicate_keys(coin_list)
    # apply duplicity overrides
    buckets["_override"] = apply_duplicity_overrides(coin_list)
    sort_coin_infos(all_coins)

    return all_coins, buckets


def coin_info() -> CoinsInfo:
    """Collects coin info, fills out support info and returns the result.

    Does not auto-delete duplicates. This should now be based on support info.
    """
    all_coins, _ = coin_info_with_duplicates()
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
