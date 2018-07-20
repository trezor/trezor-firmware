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
    if len(path) == 1 and path[0].startswith("/"):
        filename = path[0]
    else:
        filename = os.path.join(DEFS_DIR, *path)

    with open(filename) as f:
        return json.load(f, object_pairs_hook=OrderedDict)


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
        raise ValueError("Value not allowed, use one of: {}".format(", ".join(choice)))


def check_key(key, types, **kwargs):
    def do_check(coin):
        if not key in coin:
            raise KeyError("{}: Missing key".format(key))
        try:
            check_type(coin[key], types, **kwargs)
        except Exception as e:
            raise ValueError("{}: {}".format(key, e)) from e

    return do_check


COIN_CHECKS = [
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
    check_key("address_prefix", str, regex=r":$"),
    check_key("min_address_length", int),
    check_key("max_address_length", int),
    check_key("bech32_prefix", str, nullable=True),
    check_key("cashaddr_prefix", str, nullable=True),
    check_key("bitcore", list, empty=True),
    check_key("blockbook", list, empty=True),
]


def validate_coin(coin):
    errors = []
    for check in COIN_CHECKS:
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


def get_coins():
    coins = []
    for filename in glob.glob(os.path.join(DEFS_DIR, "coins", "*.json")):
        coin = load_json(filename)
        coin.update(
            name=coin["coin_name"],
            shortcut=coin["coin_shortcut"],
            key="btc:{}".format(coin["coin_shortcut"]),
        )
        coins.append(coin)

    return coins


def get_ethereum_networks():
    networks = load_json("ethereum", "networks.json")
    for network in networks:
        network.update(key="eth:{}".format(network["shortcut"]))
    return networks


def get_erc20_tokens():
    networks = get_ethereum_networks()
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


def get_nem_mosaics():
    mosaics = load_json("nem", "nem_mosaics.json")
    for mosaic in mosaics:
        shortcut = mosaic["ticker"].strip()
        mosaic.update(shortcut=shortcut, key="nem:{}".format(shortcut))
    return mosaics


def get_others():
    others = load_json("others.json")
    for other in others:
        other.update(key="network:{}".format(other["shortcut"]))
    return others


# ====== support info ======

RELEASES_URL = "https://wallet.trezor.io/data/firmware/{}/releases.json"
ETHEREUM_TOKENS = {
    "1": "https://raw.githubusercontent.com/trezor/trezor-mcu/v{}/firmware/ethereum_tokens.c",
    "2": "https://raw.githubusercontent.com/trezor/trezor-core/v{}/src/apps/ethereum/tokens.py",
}

TOKEN_MATCH = {
    "1": re.compile(r'\{.*" ([^"]+)".*\},'),
    "2": re.compile(r'\(.*["\']([^"\']+)["\'].*\),'),
}


def latest_releases():
    if not requests:
        raise RuntimeError("requests library is required for getting release info")

    latest = {}
    for v in ("1", "2"):
        releases = requests.get(RELEASES_URL.format(v)).json()
        latest[v] = max(tuple(r["version"]) for r in releases)
    return latest


def support_info_erc20(coins, versions):
    supported_tokens = {}
    for trezor, version in versions.items():
        tokens = set()
        version_str = ".".join(map(str, version))

        token_file = requests.get(ETHEREUM_TOKENS[trezor].format(version_str)).text
        token_match = TOKEN_MATCH[trezor]

        for line in token_file.split("\n"):
            m = token_match.search(line)
            if m:
                tokens.add(m.group(1))

        supported_tokens[trezor] = tokens

    support = {}
    for coin in coins:
        key = coin["key"]
        if not key.startswith("erc20:"):
            continue

        support[key] = dict(
            trezor1="yes" if coin["shortcut"] in supported_tokens["1"] else "soon",
            trezor2="yes" if coin["shortcut"] in supported_tokens["2"] else "soon",
        )

    return support


def support_info(coins, erc20_versions=None):
    support_data = load_json("support.json")
    support = {}
    for coin in coins:
        key = coin["key"]
        typ = key.split(":", maxsplit=1)[0]
        if key in support_data:
            support[key] = support_data[key]

        elif typ in ("nem", "eth"):
            support[key] = dict(trezor1="yes", trezor2="yes")

        elif typ == "erc20":
            # you must call a separate function to get that
            continue

        else:
            log.warning("support info missing for {}".format(key))
            support[key] = {}

    if erc20_versions:
        erc20 = support_info_erc20(coins, erc20_versions)
        erc20.update(support)
        return erc20
    else:
        return support


# ====== data cleanup functions ======


def find_address_collisions(coins):
    slip44 = defaultdict(list)
    at_p2pkh = defaultdict(list)
    at_p2sh = defaultdict(list)

    for name, coin in coins.items():
        s = coin["slip44"]
        # ignore m/1 testnets
        if not (name.endswith("Testnet") and s == 1):
            slip44[s].append(s)

        # skip address types on cashaddr currencies
        if coin["cashaddr_prefix"]:
            continue

        at_p2pkh[coin["address_type"]].append(name)
        at_p2sh[coin["address_type_p2sh"]].append(name)

    def prune(d):
        ret = d.copy()
        for key in d.keys():
            if len(d[key]) < 2:
                del ret[key]
        return ret

    return dict(
        slip44=prune(slip44),
        address_type=prune(at_p2pkh),
        address_type_p2sh=prune(at_p2sh),
    )


def ensure_mandatory_values(coins):
    for coin in coins:
        if not all(coin.get(k) for k in ("name", "shortcut", "key")):
            raise ValueError(coin)


def filter_duplicate_shortcuts(coins):
    dup_keys = set()
    retained_coins = OrderedDict()

    for coin in coins:
        key = coin["shortcut"]
        if key in dup_keys:
            pass
        elif key in retained_coins:
            dup_keys.add(key)
            del retained_coins[key]
        else:
            retained_coins[key] = coin

    # modify original list
    coins[:] = retained_coins.values()
    # return duplicates
    return dup_keys


def _btc_sort_key(coin):
    if coin["name"] in ("Bitcoin", "Testnet"):
        return "000000" + coin["name"]
    else:
        return coin["name"]


def get_all():
    all_coins = dict(
        btc=get_coins(),
        eth=get_ethereum_networks(),
        erc20=get_erc20_tokens(),
        nem=get_nem_mosaics(),
        other=get_others(),
    )

    for k, coins in all_coins.items():
        if k == "btc":
            coins.sort(key=_btc_sort_key)
        else:
            coins.sort(key=lambda c: c["key"].upper())

        ensure_mandatory_values(coins)
        if k != "eth":
            dup_keys = filter_duplicate_shortcuts(coins)
            if dup_keys:
                log.warning(
                    "{}: removing duplicate symbols: {}".format(k, ", ".join(dup_keys))
                )

    return all_coins


def get_list():
    all_coins = get_all()
    return sum(all_coins.values(), [])


def get_dict():
    return {coin["key"]: coin for coin in get_list()}
