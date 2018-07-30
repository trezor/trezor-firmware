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


SUPPORT_CHECKS = [
    check_key("trezor1", str, nullable=True, regex=r"^soon|planned|\d+\.\d+\.\d+$"),
    check_key("trezor2", str, nullable=True, regex=r"^soon|planned|\d+\.\d+\.\d+$"),
    check_key("webwallet", bool, nullable=True),
    check_key("connect", bool, nullable=True),
    check_key("other", dict, optional=True, empty=False),
]


def validate_support(support):
    errors = []
    for check in SUPPORT_CHECKS:
        try:
            check(support)
        except Exception as e:
            errors.append(str(e))
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
ETHEREUM_TOKENS = {
    "1": "https://raw.githubusercontent.com/trezor/trezor-mcu/v{}/firmware/ethereum_tokens.c",
    "2": "https://raw.githubusercontent.com/trezor/trezor-core/v{}/src/apps/ethereum/tokens.py",
}

TOKEN_MATCH = {
    "1": re.compile(r'\{.*" ([^"]+)".*\},'),
    "2": re.compile(r'\(.*["\']([^"\']+)["\'].*\),'),
}


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


def support_info_erc20(coins, versions):
    """Generate support info for ERC20 tokens.

    Takes a dict of Trezor versions as returned from `latest_releases`
    and a list of coins as returned from `_get_erc20_tokens` and creates
    a supportinfo entry for each listed token.

    Support status is determined by downloading and parsing the definition file
    from the appropriate firmware version. If a given token is listed, the support
    is marked as "yes". If not, support is marked as "soon", assuming that
    it will be included in next release.

    This is currently the only way to get the list of supported tokens. We don't want
    to track support individually in support.json.
    """
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


def support_info(coins, erc20_versions=None, skip_missing=False):
    """Generate Trezor support information.

    Takes a collection of coins and generates a support-info entry for each.
    The support-info is a dict with a number of known keys:
    `trezor1`, `trezor2`, `webwallet`, `connect`. An optional `other` entry
    is a dict of name-url pairs for third-party software.

    The `coins` argument can be a `CoinsInfo` object, a list or a dict of
    coin items.

    For btc-like coins and misc networks, this is taken from `support.json`.
    For NEM mosaics and ethereum networks, the support is presumed to be "yes"
    for both Trezors. Webwallet and Connect info is not filled out.

    ERC20 tokens are ignored by this function, as if `skip_missing` was true
    (see below). However, if you pass the optional `erc20_versions` argument,
    it will call `support_info_erc20` for you with given versions.

    In all cases, if the coin is explicitly listed in `support.json`, the info
    takes precedence over any other source (be it assumed "yes" for nem/eth,
    or downloaded info for erc20).

    If `skip_missing` is `True`, coins for which no support information is available
    will not be included in the output. Otherwise, an empty dict will be included
    and a warning emitted. "No support information" means that the coin is not
    listed in `support.json` and we have no heuristic to determine the support.
    """
    if isinstance(coins, CoinsInfo):
        coins = coins.as_list()
    elif isinstance(coins, dict):
        coins = coins.values()

    support_data = get_support_data()
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

        elif not skip_missing:
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


def _filter_duplicate_shortcuts(coins):
    """Removes coins with identical `shortcut`s.
    This is used to drop colliding ERC20 tokens.
    """
    dup_keys = set()
    retained_coins = OrderedDict()

    for coin in coins:
        if "Testnet" in coin["name"] and coin["shortcut"] == "tETH":
            # special case for Ethereum testnets
            continue

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
    """Returns all definition as dict organized by coin type.
    `coins` for btc-like coins,
    `eth` for ethereum networks,
    `erc20` for ERC20 tokens,
    `nem` for NEM mosaics,
    `misc` for other networks.
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
        else:
            coins.sort(key=lambda c: c["key"].upper())

        _ensure_mandatory_values(coins)
        dup_keys = _filter_duplicate_shortcuts(coins)
        if dup_keys:
            if k == "erc20":
                severity = logging.INFO
            else:
                severity = logging.WARNING
            dup_str = ", ".join(dup_keys)
            log.log(severity, "{}: removing duplicate symbols: {}".format(k, dup_str))

    return all_coins
