#!/usr/bin/env python3
from binascii import unhexlify
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
    `coins` for btc-like coins,
    `eth` for ethereum networks,
    `erc20` for ERC20 tokens,
    `nem` for NEM mosaics,
    `misc` for other networks.

    Accessible as a dict or by attribute: `info["coins"] == info.coins`
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
        raise TypeError(f"Wrong type (expected: {types})")

    # check empty
    if isinstance(val, (list, dict)) and not empty and not val:
        raise ValueError("Empty collection")

    # check regex
    if regex is not None:
        if types is not str:
            raise TypeError("Wrong type for regex check")
        if not re.search(regex, val):
            raise ValueError(f"Value does not match regex {regex}")

    # check choice
    if choice is not None and val not in choice:
        choice_str = ", ".join(choice)
        raise ValueError(f"Value not allowed, use one of: {choice_str}")


def check_key(key, types, optional=False, **kwargs):
    def do_check(coin):
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
    check_key("coin_label", str, regex=r"^[A-Z]"),
    check_key("website", str, regex=r"^http.*[^/]$"),
    check_key("github", str, regex=r"^https://github.com/.*[^/]$"),
    check_key("maintainer", str),
    check_key(
        "curve_name", str, choice=["secp256k1", "secp256k1_decred", "secp256k1_groestl"]
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
    check_key("version_group_id", int, nullable=True),
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
            name=coin["coin_name"],
            shortcut=coin["coin_shortcut"],
            key="coin:{}".format(coin["coin_shortcut"]),
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
                address_bytes=unhexlify(token["address"][2:]),
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
        latest[v] = max(tuple(r["version"]) for r in releases)
    return latest


def support_info_single(support_data, coin):
    """Extract a support dict from `support.json` data.

    Returns a dict of support values for each "device", i.e., `support.json`
    top-level key.

    The support value for each device is determined in order of priority:
    * if the coin is marked as duplicate, all support values are `None`
    * if the coin has an entry in `unsupported`, its support is `None`
    * if the coin has an entry in `supported` its support is that entry
      (usually a version string, or `True` for connect/webwallet)
    * otherwise support is presumed "soon"
    """
    support_info = {}
    key = coin["key"]
    dup = coin.get("duplicate")
    for device, values in support_data.items():
        if dup:
            support_value = None
        elif key in values["unsupported"]:
            support_value = None
        elif key in values["supported"]:
            support_value = values["supported"][key]
        else:
            support_value = "soon"
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


def find_address_collisions(coins):
    """Detects collisions in:
    - SLIP44 path prefixes
    - address type numbers, both for p2pkh and p2sh
    """
    slip44 = defaultdict(list)
    at_p2pkh = defaultdict(list)
    at_p2sh = defaultdict(list)

    for coin in coins:
        name = coin["name"]
        s = coin["slip44"]
        # ignore m/1 testnets
        if not (name.endswith("Testnet") and s == 1):
            slip44[s].append(name)

        # skip address types on cashaddr currencies
        if coin["cashaddr_prefix"]:
            continue

        at_p2pkh[coin["address_type"]].append(name)
        at_p2sh[coin["address_type_p2sh"]].append(name)

    def prune(d):
        ret = d.copy()
        for key in d:
            if len(d[key]) < 2:
                del ret[key]
        return ret

    return dict(
        slip44=prune(slip44),
        address_type=prune(at_p2pkh),
        address_type_p2sh=prune(at_p2sh),
    )


def _ensure_mandatory_values(coins):
    """Checks that every coin has the mandatory fields: name, shortcut, key"""
    for coin in coins:
        if not all(coin.get(k) for k in ("name", "shortcut", "key")):
            raise ValueError(coin)


def mark_duplicate_shortcuts(coins):
    """Finds coins with identical `shortcut`s.
    Updates their keys and sets a `duplicate` field.
    """
    dup_symbols = defaultdict(list)
    dup_keys = defaultdict(list)

    def dups_only(dups):
        return {k: v for k, v in dups.items() if len(v) > 1}

    for coin in coins:
        symsplit = coin["shortcut"].split(" ", maxsplit=1)
        symbol = symsplit[0]
        dup_symbols[symbol].append(coin)
        dup_keys[coin["key"]].append(coin)

    dup_symbols = dups_only(dup_symbols)
    dup_keys = dups_only(dup_keys)

    # mark duplicate symbols
    for values in dup_symbols.values():
        for coin in values:
            coin["duplicate"] = True

    # deduplicate keys
    for values in dup_keys.values():
        for i, coin in enumerate(values):
            # presumably only duplicate symbols can have duplicate keys
            assert coin.get("duplicate")
            coin["key"] += f":{i}"

    return dup_symbols


def _btc_sort_key(coin):
    if coin["name"] in ("Bitcoin", "Testnet"):
        return "000000" + coin["name"]
    else:
        return coin["name"]


def get_all(deduplicate=True):
    """Returns all definition as dict organized by coin type.
    `coins` for btc-like coins,
    `eth` for ethereum networks,
    `erc20` for ERC20 tokens,
    `nem` for NEM mosaics,
    `misc` for other networks.

    Automatically removes duplicate symbols from the result.
    """
    all_coins = CoinsInfo(
        coins=_load_btc_coins(),
        eth=_load_ethereum_networks(),
        erc20=_load_erc20_tokens(),
        nem=_load_nem_mosaics(),
        misc=_load_misc(),
    )

    for k, coins in all_coins.items():
        if k == "coins":
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

    if deduplicate:
        mark_duplicate_shortcuts(all_coins.as_list())
        all_coins["erc20"] = [
            coin for coin in all_coins["erc20"] if not coin.get("duplicate")
        ]

    return all_coins
