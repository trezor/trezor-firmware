#!/usr/bin/env python3
import glob
import json
import logging
import os
import re
from collections import OrderedDict, defaultdict

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
    if isinstance(val, str) and not empty and not val:
        raise ValueError("Empty string")

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

    for bc in coin["bitcore"] + coin["blockbook"]:
        if not bc.startswith("https://"):
            errors.append("make sure URLs start with https://")

        if bc.endswith("/"):
            errors.append("make sure URLs don't end with '/'")

    return errors


# ======= Coin json loaders =======


def _load_btc_coins():
    """Load btc-like coins from `bitcoin/*.json`"""
    coins = []
    for filename in glob.glob(os.path.join(DEFS_DIR, "bitcoin", "*.json")):
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
        chain = network["chain"]

        chain_path = os.path.join(DEFS_DIR, "ethereum", "tokens", "tokens", chain)
        for filename in sorted(glob.glob(os.path.join(chain_path, "*.json"))):
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


def _load_fido_apps():
    """Load FIDO apps from `fido/*.json`"""
    apps = []
    for filename in sorted(glob.glob(os.path.join(DEFS_DIR, "fido", "*.json"))):
        app_name = os.path.basename(filename)[:-5].lower()
        app = load_json(filename)
        app.setdefault("use_sign_count", None)
        app.setdefault("use_self_attestation", None)
        app.setdefault("u2f", [])
        app.setdefault("webauthn", [])

        icon_path = os.path.join(DEFS_DIR, "fido", app_name + ".png")
        if not os.path.exists(icon_path):
            icon_path = None

        app.update(key=app_name, icon=icon_path)
        apps.append(app)

    return apps


# ====== support info ======

RELEASES_URL = "https://beta-wallet.trezor.io/data/firmware/{}/releases.json"
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
        if key in values["unsupported"]:
            support_value = False
        elif key in values["supported"]:
            support_value = values["supported"][key]
        elif device in MISSING_SUPPORT_MEANS_NO:
            support_value = False
        elif is_token(coin):
            if dup:
                # if duplicate token that is not explicitly listed, it's unsupported
                support_value = False
            else:
                # otherwise implicitly supported in next
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
    """Finds coins with identical symbols and sets their `duplicate` field.

    "Symbol" here means the first part of `shortcut` (separated by space),
    so, e.g., "BTL (Battle)" and "BTL (Bitlle)" have the same symbol "BTL".

    The result of this function is a dictionary of _buckets_, each of which is
    indexed by the duplicated symbol, or `_override`. The `_override` bucket will
    contain all coins that are set to `true` in `duplicity_overrides.json`.

    Each coin in every bucket will have its "duplicate" property set to True, unless
    it's explicitly marked as `false` in `duplicity_overrides.json`.
    """
    dup_symbols = defaultdict(list)

    for coin in coins:
        symbol, _ = symbol_from_shortcut(coin["shortcut"].lower())
        dup_symbols[symbol].append(coin)

    dup_symbols = {k: v for k, v in dup_symbols.items() if len(v) > 1}

    # load overrides and put them into their own bucket
    overrides = load_json("duplicity_overrides.json")
    override_bucket = []
    for coin in coins:
        if overrides.get(coin["key"], False):
            coin["duplicate"] = True
            override_bucket.append(coin)

    # mark duplicate symbols
    for values in dup_symbols.values():
        for coin in values:
            # allow overrides to skip this; if not listed in overrides, assume True
            is_dup = overrides.get(coin["key"], True)
            if is_dup:
                coin["duplicate"] = True
            # again: still in dups, but not marked as duplicate and not deleted

    dup_symbols["_override"] = override_bucket
    return dup_symbols


def deduplicate_erc20(buckets, networks):
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

    testnet_networks = {n["chain"] for n in networks if "Testnet" in n["name"]}
    overrides = buckets["_override"]

    def clear_bucket(bucket):
        # allow all coins, except those that are explicitly marked through overrides
        for coin in bucket:
            if coin not in overrides:
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


def deduplicate_keys(all_coins):
    dups = defaultdict(list)
    for coin in all_coins:
        dups[coin["key"]].append(coin)

    for coins in dups.values():
        if len(coins) <= 1:
            continue
        for i, coin in enumerate(coins):
            if is_token(coin):
                coin["key"] += ":" + coin["address"][2:6].lower()  # first 4 hex chars
            else:
                coin["key"] += ":{}".format(i)
                coin["dup_key_nontoken"] = True


def _btc_sort_key(coin):
    if coin["name"] in ("Bitcoin", "Testnet", "Regtest"):
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
    """
    all_coins = CoinsInfo(
        bitcoin=_load_btc_coins(),
        eth=_load_ethereum_networks(),
        erc20=_load_erc20_tokens(),
        nem=_load_nem_mosaics(),
        misc=_load_misc(),
    )

    for k, coins in all_coins.items():
        _ensure_mandatory_values(coins)

    return all_coins


def sort_coin_infos(all_coins):
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


def coin_info_with_duplicates():
    """Collects coin info, detects duplicates but does not remove them.

    Returns the CoinsInfo object and duplicate buckets.
    """
    all_coins = collect_coin_info()
    buckets = mark_duplicate_shortcuts(all_coins.as_list())
    deduplicate_erc20(buckets, all_coins.eth)
    deduplicate_keys(all_coins.as_list())
    sort_coin_infos(all_coins)

    return all_coins, buckets


def coin_info():
    """Collects coin info, fills out support info and returns the result.

    Does not auto-delete duplicates. This should now be based on support info.
    """
    all_coins, _ = coin_info_with_duplicates()
    # all_coins["erc20"] = [
    #     coin for coin in all_coins["erc20"] if not coin.get("duplicate")
    # ]
    return all_coins


def fido_info():
    """Returns info about known FIDO/U2F apps."""
    return _load_fido_apps()


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
