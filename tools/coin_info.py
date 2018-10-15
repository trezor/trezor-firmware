#!/usr/bin/env python3
from collections import defaultdict, OrderedDict
import re
import os
import json
import glob
import logging

try:
    import requests
except ImportError:
    requests = None

log = logging.getLogger(__name__)

DEFS_DIR = os.path.abspath(
    os.environ.get("DEFS_DIR") or os.path.join(os.path.dirname(__file__), "..", "defs")
)


def load_json(*path):
    """Convenience function to load a JSON file from DEFS_DIR."""
    if len(path) == 1 and path[0].startswith("/"):
        filename = path[0]
    else:
        filename = os.path.join(DEFS_DIR, *path)

    with open(filename) as f:
        return json.load(f, object_pairs_hook=OrderedDict)


# ====== CoinsInfo ======


class CoinsInfo(dict):
    """Collection of information about all known kinds of coins.

    It contains the following lists:
    `bitcoin` for btc-like coins,
    `eth` for ethereum networks,
    `erc20` for ERC20 tokens,
    `nem` for NEM mosaics,
    `misc` for other networks.

    Accessible as a dict or by attribute: `info["misc"] == info.misc`
    """

    def as_list(self):
        return sum(self.values(), [])

    def as_dict(self):
        return {coin["key"]: coin for coin in self.as_list()}

    def __getattr__(self, attr):
        if attr in self:
            return self[attr]
        else:
            raise AttributeError(attr)


# ====== coin validation ======


def check_type(val, types, nullable=False, empty=False, regex=None, choice=None):
    # check nullable
    if val is None:
        if nullable:
            return
        else:
            raise ValueError("Missing required value")

    # check type
    if not isinstance(val, types):
        raise TypeError("Wrong type (expected: {})".format(types))

    # check empty
    if isinstance(val, (list, dict)) and not empty and not val:
        raise ValueError("Empty collection")

    # check regex
    if regex is not None:
        if types is not str:
            raise TypeError("Wrong type for regex check")
        if not re.search(regex, val):
            raise ValueError("Value does not match regex {}".format(regex))

    # check choice
    if choice is not None and val not in choice:
        choice_str = ", ".join(choice)
        raise ValueError("Value not allowed, use one of: {}".format(choice_str))


def check_key(key, types, optional=False, **kwargs):
    def do_check(coin):
        if key not in coin:
            if optional:
                return
            else:
                raise KeyError("{}: Missing key".format(key))
        try:
            check_type(coin[key], types, **kwargs)
        except Exception as e:
            raise ValueError("{}: {}".format(key, e)) from e

    return do_check


BTC_CHECKS = [
    check_key("coin_name", str, regex=r"^[A-Z]"),
    check_key("coin_shortcut", str, regex=r"^t?[A-Z]{3,}$"),
    check_key("coin_label", str, regex=r"^[A-Z]"),
    check_key("website", str, regex=r"^http.*[^/]$"),
    check_key("github", str, regex=r"^https://github.com/.*[^/]$"),
    check_key("maintainer", str),
    check_key(
        "curve_name", str, choice=["secp256k1", "secp256k1_decred", "secp256k1_groestl", "secp256k1_smart"]
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
    check_key("bip115", bool),
    check_key("default_fee_b", dict),
    check_key("dust_limit", int),
    check_key("blocktime_seconds", int),
    check_key("signed_message_header", str),
    check_key("uri_prefix", str, regex=r"^[a-z]+$"),
    check_key("min_address_length", int),
    check_key("max_address_length", int),
    check_key("bech32_prefix", str, regex=r"^[a-z]+$", nullable=True),
    check_key("cashaddr_prefix", str, regex=r"^[a-z]+$", nullable=True),
    check_key("bitcore", list, empty=True),
    check_key("blockbook", list, empty=True),
]


def validate_btc(coin):
    errors = []
    for check in BTC_CHECKS:
        try:
            check(coin)
        except Exception as e:
            errors.append(str(e))

    magics = [
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

    for bc in coin["bitcore"] + coin["blockbook"]:
        if bc.endswith("/"):
            errors.append("make sure URLs don't end with '/'")

    return errors


# ======= Coin json loaders =======


def _load_btc_coins():
    """Load btc-like coins from `coins/*.json`"""
    coins = []
    for filename in glob.glob(os.path.join(DEFS_DIR, "coins", "*.json")):
        coin = load_json(filename)
        coin.update(
            name=coin["coin_label"],
            shortcut=coin["coin_shortcut"],
            key="bitcoin:{}".format(coin["coin_shortcut"]),
            icon=filename.replace(".json", ".png"),
        )
        coins.append(coin)

    return coins


def _load_ethereum_networks():
    """Load ethereum networks from `ethereum/networks.json`"""
    networks = load_json("ethereum", "networks.json")
    for network in networks:
        network.update(key="eth:{}".format(network["shortcut"]))
    return networks


def _load_erc20_tokens():
    """Load ERC20 tokens from `ethereum/tokens` submodule."""
    networks = _load_ethereum_networks()
    tokens = []
    for network in networks:
        if network["name"].startswith("Ethereum Testnet "):
            idx = len("Ethereum Testnet ")
            chain = network["name"][idx : idx + 3]
        else:
            chain = network["shortcut"]
        chain = chain.lower()
        if not chain:
            continue

        chain_path = os.path.join(DEFS_DIR, "ethereum", "tokens", "tokens", chain)
        for filename in glob.glob(os.path.join(chain_path, "*.json")):
            token = load_json(filename)
            token.update(
                chain=chain,
                chain_id=network["chain_id"],
                address_bytes=bytes.fromhex(token["address"][2:]),
                shortcut=token["symbol"],
                key="erc20:{}:{}".format(chain, token["symbol"]),
            )
            tokens.append(token)

    return tokens


def _load_nem_mosaics():
    """Loads NEM mosaics from `nem/nem_mosaics.json`"""
    mosaics = load_json("nem", "nem_mosaics.json")
    for mosaic in mosaics:
        shortcut = mosaic["ticker"].strip()
        mosaic.update(shortcut=shortcut, key="nem:{}".format(shortcut))
    return mosaics


def _load_misc():
    """Loads miscellaneous networks from `misc/misc.json`"""
    others = load_json("misc/misc.json")
    for other in others:
        other.update(key="misc:{}".format(other["shortcut"]))
    return others


# ====== support info ======

RELEASES_URL = "https://wallet.trezor.io/data/firmware/{}/releases.json"
MISSING_SUPPORT_MEANS_NO = ("connect", "webwallet")
VERSIONED_SUPPORT_INFO = ("trezor1", "trezor2")


def get_support_data():
    """Get raw support data from `support.json`."""
    return load_json("support.json")


def latest_releases():
    """Get latest released firmware versions for Trezor 1 and 2"""
    if not requests:
        raise RuntimeError("requests library is required for getting release info")

    latest = {}
    for v in ("1", "2"):
        releases = requests.get(RELEASES_URL.format(v)).json()
        latest["trezor" + v] = max(tuple(r["version"]) for r in releases)
    return latest


def is_token(coin):
    return coin["key"].startswith("erc20:")


def support_info_single(support_data, coin):
    """Extract a support dict from `support.json` data.

    Returns a dict of support values for each "device", i.e., `support.json`
    top-level key.

    The support value for each device is determined in order of priority:
    * if the coin is a duplicate ERC20 token, all support values are `None`
    * if the coin has an entry in `unsupported`, its support is `None`
    * if the coin has an entry in `supported` its support is that entry
      (usually a version string, or `True` for connect/webwallet)
    * otherwise support is presumed "soon"
    """
    support_info = {}
    key = coin["key"]
    dup = coin.get("duplicate")
    for device, values in support_data.items():
        if dup and is_token(coin):
            support_value = False
        elif key in values["unsupported"]:
            support_value = False
        elif key in values["supported"]:
            support_value = values["supported"][key]
        elif device in MISSING_SUPPORT_MEANS_NO:
            support_value = False
        elif is_token(coin):
            # tokens are implicitly supported in next release
            support_value = "soon"
        else:
            support_value = None
        support_info[device] = support_value
    return support_info


def support_info(coins):
    """Generate Trezor support information.

    Takes a collection of coins and generates a support-info entry for each.
    The support-info is a dict with keys based on `support.json` keys.
    These are usually: "trezor1", "trezor2", "connect" and "webwallet".

    The `coins` argument can be a `CoinsInfo` object, a list or a dict of
    coin items.

    Support information is taken from `support.json`.
    """
    if isinstance(coins, CoinsInfo):
        coins = coins.as_list()
    elif isinstance(coins, dict):
        coins = coins.values()

    support_data = get_support_data()
    support = {}
    for coin in coins:
        support[coin["key"]] = support_info_single(support_data, coin)

    return support


# ====== data cleanup functions ======


def _ensure_mandatory_values(coins):
    """Checks that every coin has the mandatory fields: name, shortcut, key"""
    for coin in coins:
        if not all(coin.get(k) for k in ("name", "shortcut", "key")):
            raise ValueError(coin)


def symbol_from_shortcut(shortcut):
    symsplit = shortcut.split(" ", maxsplit=1)
    return symsplit[0], symsplit[1] if len(symsplit) > 1 else ""


def mark_duplicate_shortcuts(coins):
    """Finds coins with identical `shortcut`s.
    Updates their keys and sets a `duplicate` field.

    The logic is a little crazy.

    The result of this function is a dictionary of _buckets_, each of which is
    indexed by the duplicated symbol, or `_override`. The `_override` bucket will
    contain all coins that are set to `true` in `duplicity_overrides.json`. These
    will _always_ be marked as duplicate (and later possibly deleted if they're ERC20).

    The rest will disambiguate based on the full shortcut.
    (i.e., when `shortcut` is `BTL (Battle)`, the `symbol` is just `BTL`).
    If _all tokens_ in the bucket have shortcuts with distinct suffixes, e.g.,
    `CAT (BitClave)` and `CAT (Blockcat)`, we DO NOT mark them as duplicate.
    These will then be supported and included in outputs.

    If even one token in the bucket _does not_ have a distinct suffix, e.g.,
    `MIT` and `MIT (Mychatcoin)`, the whole bucket is marked as duplicate.

    If a token is set to `false` in `duplicity_overrides.json`, it will NOT
    be marked as duplicate in this step, even if it is part of a "bad" bucket.
    """
    dup_symbols = defaultdict(list)
    dup_keys = defaultdict(list)

    def dups_only(dups):
        return {k: v for k, v in dups.items() if len(v) > 1}

    for coin in coins:
        symbol, _ = symbol_from_shortcut(coin["shortcut"].lower())
        dup_symbols[symbol].append(coin)
        dup_keys[coin["key"]].append(coin)

    dup_symbols = dups_only(dup_symbols)
    dup_keys = dups_only(dup_keys)

    # first deduplicate keys so that we can identify overrides
    for values in dup_keys.values():
        for i, coin in enumerate(values):
            coin["key"] += ":" + str(i)

    # load overrides and put them into their own bucket
    overrides = load_json("duplicity_overrides.json")
    override_bucket = []
    for coin in coins:
        if overrides.get(coin["key"], False):
            coin["duplicate"] = True
            override_bucket.append(coin)

    # mark duplicate symbols
    for values in dup_symbols.values():
        splits = (symbol_from_shortcut(coin["shortcut"]) for coin in values)
        suffixes = {suffix for _, suffix in splits}
        # if 1. all suffixes are distinct and 2. none of them are empty
        if len(suffixes) == len(values) and all(suffixes):
            # Allow the whole bucket.
            # For all intents and purposes these should be considered non-dups
            # So we won't mark them as dups here
            # But they still have their own bucket, and also overrides can
            # explicitly mark them as duplicate one step before, in which case
            # they *still* keep duplicate status (and possibly are deleted).
            continue

        for coin in values:
            # allow overrides to skip this; if not listed in overrides, assume True
            is_dup = overrides.get(coin["key"], True)
            if is_dup:
                coin["duplicate"] = True
            # again: still in dups, but not marked as duplicate and not deleted

    dup_symbols["_override"] = override_bucket
    return dup_symbols


def _btc_sort_key(coin):
    if coin["name"] in ("Bitcoin", "Testnet"):
        return "000000" + coin["name"]
    else:
        return coin["name"]


def collect_coin_info():
    """Returns all definition as dict organized by coin type.
    `coins` for btc-like coins,
    `eth` for ethereum networks,
    `erc20` for ERC20 tokens,
    `nem` for NEM mosaics,
    `misc` for other networks.

    Automatically removes duplicate symbols from the result.
    """
    all_coins = CoinsInfo(
        bitcoin=_load_btc_coins(),
        eth=_load_ethereum_networks(),
        erc20=_load_erc20_tokens(),
        nem=_load_nem_mosaics(),
        misc=_load_misc(),
    )

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

        _ensure_mandatory_values(coins)

    return all_coins


def coin_info_with_duplicates():
    """Collects coin info, detects duplicates but does not remove them.

    Returns the CoinsInfo object and duplicate buckets.
    """
    all_coins = collect_coin_info()
    buckets = mark_duplicate_shortcuts(all_coins.as_list())
    return all_coins, buckets


def coin_info():
    """Collects coin info, marks and prunes duplicate ERC20 symbols, fills out support
    info and returns the result.
    """
    all_coins, _ = coin_info_with_duplicates()
    all_coins["erc20"] = [
        coin for coin in all_coins["erc20"] if not coin.get("duplicate")
    ]
    return all_coins


def search(coins, keyword):
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
