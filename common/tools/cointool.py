#!/usr/bin/env python3
from __future__ import annotations

import datetime
import fnmatch
import json
import logging
import os
import re
import sys
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterator, TextIO, cast

import click

import coin_info
from coin_info import Coin, CoinBuckets, Coins, CoinsInfo, FidoApps, SupportInfo

DEFINITIONS_TIMESTAMP_PATH = (
    coin_info.DEFS_DIR / "ethereum" / "released-definitions-timestamp.txt"
)
DEFINITIONS_LATEST_URL = (
    "https://raw.githubusercontent.com/trezor/definitions/main/definitions-latest.json"
)

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent

try:
    import termcolor
except ImportError:
    termcolor = None

try:
    import mako
    import mako.template
    from munch import Munch

    CAN_RENDER = True
except ImportError:
    CAN_RENDER = False

try:
    import requests
except ImportError:
    requests = None

try:
    from PIL import Image

    CAN_CHECK_ICONS = True
except ImportError:
    CAN_CHECK_ICONS = False


# ======= Crayon colors ======
USE_COLORS = False


def crayon(
    color: str | None, string: str, bold: bool = False, dim: bool = False
) -> str:
    if not termcolor or not USE_COLORS:
        return string
    else:
        if bold:
            attrs = ["bold"]
        elif dim:
            attrs = ["dark"]
        else:
            attrs = []
        return termcolor.colored(string, color, attrs=attrs)


def print_log(level: int, *args: Any, **kwargs: Any) -> None:
    prefix = logging.getLevelName(level)
    if level == logging.DEBUG:
        prefix = crayon("blue", prefix, bold=False)
    elif level == logging.INFO:
        prefix = crayon("blue", prefix, bold=True)
    elif level == logging.WARNING:
        prefix = crayon("red", prefix, bold=False)
    elif level == logging.ERROR:
        prefix = crayon("red", prefix, bold=True)
    print(prefix, *args, **kwargs)


# ======= Mako management ======


def c_str_filter(b: Any) -> str:
    if b is None:
        return "NULL"

    def hexescape(c: bytes) -> str:
        return rf"\x{c:02x}"

    if isinstance(b, bytes):
        return '"' + "".join(map(hexescape, b)) + '"'
    else:
        return json.dumps(b)


def black_repr_filter(val: Any) -> str:
    if isinstance(val, str):
        if '"' in val:
            return repr(val)
        else:
            return c_str_filter(val)
    elif isinstance(val, bytes):
        return "b" + c_str_filter(val)
    else:
        return repr(val)


def ascii_filter(s: str) -> str:
    return re.sub("[^ -\x7e]", "_", s)


def utf8_str_filter(s: str) -> str:
    return '"' + repr(s)[1:-1] + '"'


def make_support_filter(
    support_info: SupportInfo,
) -> Callable[[str, Coins], Iterator[Coin]]:
    def supported_on(device: str, coins: Coins) -> Iterator[Coin]:
        return (c for c in coins if support_info[c.key].get(device))

    return supported_on


MAKO_FILTERS = {
    "utf8_str": utf8_str_filter,
    "c_str": c_str_filter,
    "ascii": ascii_filter,
    "black_repr": black_repr_filter,
}


def render_file(
    src: Path, dst: Path, coins: CoinsInfo, support_info: SupportInfo, models: list[str]
) -> None:
    """Renders `src` template into `dst`.

    `src` is a filename, `dst` is an open file object.
    """
    template = mako.template.Template(filename=str(src.resolve()))
    eth_defs_date = datetime.datetime.fromisoformat(
        DEFINITIONS_TIMESTAMP_PATH.read_text().strip()
    )
    this_file = Path(src)
    result = template.render(
        support_info=support_info,
        supported_on=make_support_filter(support_info),
        ethereum_defs_timestamp=int(eth_defs_date.timestamp()),
        THIS_FILE=this_file,
        ROOT=ROOT,
        **coins,
        **MAKO_FILTERS,
        ALL_MODELS=models,
    )
    dst.write_text(str(result))
    src_stat = src.stat()
    os.utime(dst, ns=(src_stat.st_atime_ns, src_stat.st_mtime_ns))


# ====== validation functions ======


def mark_unsupported(support_info: SupportInfo, coins: Coins) -> None:
    for coin in coins:
        key = coin["key"]
        # checking for explicit False because None means unknown
        coin["unsupported"] = all(v is False for v in support_info[key].values())


def highlight_key(coin: Coin, color: str) -> str:
    """Return a colorful string where the SYMBOL part is bold."""
    keylist = coin["key"].split(":")
    if keylist[-1].isdigit():
        keylist[-2] = crayon(color, keylist[-2], bold=True)
    else:
        keylist[-1] = crayon(color, keylist[-1], bold=True)
    key = crayon(color, ":".join(keylist))
    name = crayon(None, f"({coin['name']})", dim=True)
    return f"{key} {name}"


def find_collisions(coins: Coins, field: str) -> CoinBuckets:
    """Detects collisions in a given field. Returns buckets of colliding coins."""
    collisions: CoinBuckets = defaultdict(list)
    for coin in coins:
        values = coin[field]
        if not isinstance(values, list):
            values = [values]
        for value in values:
            collisions[value].append(coin)
    return {k: v for k, v in collisions.items() if len(v) > 1}


def check_eth(coins: Coins) -> bool:
    check_passed = True
    chains = find_collisions(coins, "chain")
    for key, bucket in chains.items():
        bucket_str = ", ".join(f"{coin['key']} ({coin['name']})" for coin in bucket)
        chain_name_str = "colliding chain name " + crayon(None, key, bold=True) + ":"
        print_log(logging.ERROR, chain_name_str, bucket_str)
        check_passed = False
    return check_passed


def check_btc(coins: Coins) -> bool:
    check_passed = True

    # validate individual coin data
    for coin in coins:
        errors = coin_info.validate_btc(coin)
        if errors:
            check_passed = False
            print_log(logging.ERROR, "invalid definition for", coin["name"])
            print("\n".join(errors))

    def collision_str(bucket: Coins) -> str:
        """Generate a colorful string out of a bucket of colliding coins."""
        coin_strings: list[str] = []
        for coin in bucket:
            name = coin["name"]
            prefix = ""
            if coin["is_testnet"]:
                color = "green"
            elif name == "Bitcoin":
                color = "red"
            elif coin["unsupported"]:
                color = "grey"
                prefix = crayon("blue", "(X)", bold=True)
            else:
                color = "blue"
            hl = highlight_key(coin, color)
            coin_strings.append(prefix + hl)
        return ", ".join(coin_strings)

    def print_collision_buckets(
        buckets: CoinBuckets,
        prefix: str,
        maxlevel: int = logging.ERROR,
        strict: bool = False,
    ) -> bool:
        """Intelligently print collision buckets.

        For each bucket, if there are any collision with a mainnet, print it.
        If the collision is with unsupported networks or testnets, it's just INFO.
        If the collision is with supported mainnets, it's WARNING.
        If the collision with any supported network includes Bitcoin, it's an ERROR.
        """
        failed = False
        for key, bucket in buckets.items():
            mainnets = [c for c in bucket if not c["is_testnet"]]

            have_bitcoin = any(coin["name"] == "Bitcoin" for coin in mainnets)
            supported_mainnets = [c for c in mainnets if not c["unsupported"]]
            supported_networks = [c for c in bucket if not c["unsupported"]]

            if len(mainnets) > 1:
                if (have_bitcoin or strict) and len(supported_networks) > 1:
                    # ANY collision with Bitcoin is bad
                    level = maxlevel
                    failed = True
                elif len(supported_mainnets) > 1:
                    # collision between supported networks is still pretty bad
                    level = logging.WARNING
                else:
                    # collision between some unsupported networks is OK
                    level = logging.INFO
                print_log(level, f"{prefix} {key}:", collision_str(bucket))

        return failed

    # slip44 collisions
    print("Checking SLIP44 values collisions...")
    slip44 = find_collisions(coins, "slip44")
    if print_collision_buckets(slip44, "value", strict=True):
        check_passed = False

    # only check address_type on coins that don't use cashaddr
    nocashaddr = [coin for coin in coins if not coin.get("cashaddr_prefix")]

    print("Checking address_type collisions...")
    address_type = find_collisions(nocashaddr, "address_type")
    if print_collision_buckets(address_type, "address type"):
        check_passed = False

    print("Checking address_type_p2sh collisions...")
    address_type_p2sh = find_collisions(nocashaddr, "address_type_p2sh")
    # we ignore failed checks on P2SH, because reasons
    print_collision_buckets(address_type_p2sh, "address type", logging.WARNING)

    print("Checking genesis block collisions...")
    genesis = find_collisions(coins, "hash_genesis_block")
    print_collision_buckets(genesis, "genesis block", logging.WARNING)

    return check_passed


def check_dups(buckets: CoinBuckets) -> bool:
    """Analyze and pretty-print results of `coin_info.mark_duplicate_shortcuts`.

    The results are buckets of colliding symbols.
    If the collision is only between ERC20 tokens, it's DEBUG.
    If the collision includes one non-token, it's INFO.
    If the collision includes more than one non-token, it's ERROR and printed always.
    """

    def coin_str(coin: Coin) -> str:
        """Colorize coins according to support / override status."""
        prefix = ""
        if coin["unsupported"]:
            color = "grey"
            prefix = crayon("blue", "(X)", bold=True)
        else:
            color = "red"

        if not coin.get("duplicate"):
            prefix = crayon("green", "*", bold=True) + prefix

        highlighted = highlight_key(coin, color)
        return f"{prefix}{highlighted}"

    check_passed = True

    for symbol in sorted(buckets.keys()):
        bucket = buckets[symbol]
        if not bucket:
            continue

        # supported coins from the bucket
        supported = [coin for coin in bucket if not coin["unsupported"]]

        # string generation
        dup_str = ", ".join(coin_str(coin) for coin in bucket)

        if any(coin.get("duplicate") for coin in supported):
            # At least one supported coin is marked as duplicate.
            level = logging.ERROR
            check_passed = False
        elif len(supported) > 1:
            # More than one supported coin in bucket, but no marked duplicates
            # --> all must have been cleared by an override.
            level = logging.INFO
        else:
            # At most 1 supported coin in bucket. This is OK.
            level = logging.DEBUG

        if symbol == "_override":
            print_log(level, "force-set duplicates:", dup_str)
        else:
            print_log(level, f"duplicate symbol {symbol.upper()}:", dup_str)

    return check_passed


def check_backends(coins: Coins) -> bool:
    check_passed = True
    for coin in coins:
        genesis_block = coin.get("hash_genesis_block")
        if not genesis_block:
            continue
        backends = coin.get("blockbook", []) + coin.get("bitcore", [])
        for backend in backends:
            print("checking", backend, "... ", end="", flush=True)
            try:
                assert requests is not None
                j = requests.get(backend + "/api/block-index/0").json()
                if j["blockHash"] != genesis_block:
                    raise RuntimeError("genesis block mismatch")
            except Exception as e:
                print(e)
                check_passed = False
            else:
                print("OK")
    return check_passed


def check_icons(coins: Coins) -> bool:
    check_passed = True
    for coin in coins:
        key = coin["key"]
        icon_file = coin.get("icon")
        if not icon_file:
            print(key, ": missing icon")
            check_passed = False
            continue

        try:
            icon = Image.open(icon_file)
        except Exception:
            print(key, ": failed to open icon file", icon_file)
            check_passed = False
            continue

        if icon.size != (96, 96) or icon.mode != "RGBA":
            print(key, ": bad icon format (must be RGBA 96x96)")
            check_passed = False
    return check_passed


IGNORE_NONUNIFORM_KEYS = frozenset(("unsupported", "duplicate", "coingecko_id"))


def check_key_uniformity(coins: Coins) -> bool:
    keysets: dict[frozenset[str], Coins] = defaultdict(list)
    for coin in coins:
        keyset = frozenset(coin.keys()) | IGNORE_NONUNIFORM_KEYS
        keysets[keyset].append(coin)

    if len(keysets) <= 1:
        return True

    buckets = list(keysets.values())
    buckets.sort(key=lambda x: len(x))
    majority = buckets[-1]
    rest = sum(buckets[:-1], [])
    reference_keyset = set(majority[0].keys()) | IGNORE_NONUNIFORM_KEYS
    print(reference_keyset)

    for coin in rest:
        key = coin["key"]
        keyset = set(coin.keys()) | IGNORE_NONUNIFORM_KEYS
        missing = ", ".join(reference_keyset - keyset)
        if missing:
            print_log(logging.ERROR, f"coin {key} has missing keys: {missing}")
        additional = ", ".join(keyset - reference_keyset)
        if additional:
            print_log(
                logging.ERROR,
                f"coin {key} has superfluous keys: {additional}",
            )

    return False


def check_segwit(coins: Coins) -> bool:
    for coin in coins:
        segwit = coin["segwit"]
        segwit_fields = [
            "bech32_prefix",
            "xpub_magic_segwit_native",
            "xpub_magic_segwit_p2sh",
            "xpub_magic_multisig_segwit_native",
            "xpub_magic_multisig_segwit_p2sh",
        ]
        if segwit:
            for field in segwit_fields:
                if coin[field] is None:
                    print_log(
                        logging.ERROR,
                        coin["name"],
                        f"segwit is True => {field} should be set",
                    )
                    return False
        else:
            for field in segwit_fields:
                if coin[field] is not None:
                    print_log(
                        logging.ERROR,
                        coin["name"],
                        f"segwit is False => {field} should NOT be set",
                    )
                    return False
    return True


FIDO_KNOWN_KEYS = frozenset(
    (
        "key",
        "u2f",
        "webauthn",
        "name",
        "use_sign_count",
        "use_self_attestation",
        "use_compact",
        "no_icon",
        "icon",
    )
)


def check_fido(apps: FidoApps) -> bool:
    check_passed = True

    u2fs = find_collisions((u for a in apps if "u2f" in a for u in a["u2f"]), "app_id")
    for key, bucket in u2fs.items():
        bucket_str = ", ".join(u2f["label"] for u2f in bucket)
        app_id_str = "colliding U2F app ID " + crayon(None, key, bold=True) + ":"
        print_log(logging.ERROR, app_id_str, bucket_str)
        check_passed = False

    webauthn_domains = find_collisions((a for a in apps if "webauthn" in a), "webauthn")
    for key, bucket in webauthn_domains.items():
        bucket_str = ", ".join(app["key"] for app in bucket)
        webauthn_str = "colliding WebAuthn domain " + crayon(None, key, bold=True) + ":"
        print_log(logging.ERROR, webauthn_str, bucket_str)
        check_passed = False

    domain_hashes: dict[bytes, str] = {}
    for app in apps:
        if "webauthn" in app:
            for domain in app["webauthn"]:
                domain_hashes[sha256(domain.encode()).digest()] = domain
    for app in apps:
        if "u2f" in app:
            for u2f in app["u2f"]:
                domain = domain_hashes.get(bytes.fromhex(u2f["app_id"]))
                if domain:
                    print_log(
                        logging.ERROR,
                        "colliding WebAuthn domain "
                        + crayon(None, domain, bold=True)
                        + " and U2F app_id "
                        + crayon(None, u2f["app_id"], bold=True)
                        + " for "
                        + u2f["label"],
                    )
                    check_passed = False

    for app in apps:
        if "name" not in app:
            print_log(logging.ERROR, app["key"], ": missing name")
            check_passed = False

        if "u2f" in app:
            for u2f in app["u2f"]:
                if "app_id" not in u2f:
                    print_log(logging.ERROR, app["key"], ": missing app_id")
                    check_passed = False

                if "label" not in u2f:
                    print_log(logging.ERROR, app["key"], ": missing label")
                    check_passed = False

        if not app.get("u2f") and not app.get("webauthn"):
            print_log(logging.ERROR, app["key"], ": no U2F nor WebAuthn addresses")
            check_passed = False

        unknown_keys = set(app.keys()) - FIDO_KNOWN_KEYS
        if unknown_keys:
            print_log(logging.ERROR, app["key"], ": unrecognized keys:", unknown_keys)
            check_passed = False

        # check icons
        if app["icon"] is None:
            if app.get("no_icon"):
                continue

            print_log(logging.ERROR, app["key"], ": missing icon")
            check_passed = False
            continue

        elif app.get("no_icon"):
            print_log(logging.ERROR, app["key"], ": icon present for 'no_icon' app")
            check_passed = False

        try:
            icon = Image.open(app["icon"])
        except Exception:
            print_log(
                logging.ERROR, app["key"], ": failed to open icon file", app["icon"]
            )
            check_passed = False
            continue

        if icon.size != (128, 128) or icon.mode != "RGBA":
            print_log(
                logging.ERROR, app["key"], ": bad icon format (must be RGBA 128x128)"
            )
            check_passed = False

    return check_passed


# ====== click command handlers ======


@click.group()
@click.option(
    "--colors/--no-colors",
    "-c/-C",
    default=sys.stdout.isatty(),
    help="Force colored output on/off",
)
def cli(colors: bool) -> None:
    global USE_COLORS
    USE_COLORS = colors


@cli.command()
# fmt: off
@click.option("--backend/--no-backend", "-b", default=False, help="Check blockbook/bitcore responses")
@click.option("--icons/--no-icons", default=True, help="Check icon files")
# fmt: on
def check(backend: bool, icons: bool) -> None:
    """Validate coin definitions.

    Checks that every btc-like coin is properly filled out, reports duplicate symbols,
    missing or invalid icons, backend responses, and uniform key information --
    i.e., that all coins of the same type have the same fields in their JSON data.

    Uniformity check ignores NEM mosaics and ERC20 tokens, where non-uniformity is
    expected.

    All shortcut collisions are shown, including colliding ERC20 tokens.

    In the output, duplicate ERC tokens will be shown in cyan; duplicate non-tokens
    in red. An asterisk (*) next to symbol name means that even though it was detected
    as duplicate, it is still included in results.

    The collision detection checks that SLIP44 numbers don't collide between different
    mainnets (testnet collisions are allowed), that `address_prefix` doesn't collide
    with Bitcoin (other collisions are reported as warnings). `address_prefix_p2sh`
    is also checked but we have a bunch of collisions there and can't do much
    about them, so it's not an error.

    In the collision checks, Bitcoin is shown in red, other mainnets in blue,
    testnets in green and unsupported networks in gray, marked with `(X)` for
    non-colored output.
    """
    if backend and requests is None:
        raise click.ClickException("You must install requests for backend check")

    if icons and not CAN_CHECK_ICONS:
        raise click.ClickException("Missing requirements for icon check")

    defs, buckets = coin_info.coin_info_with_duplicates()
    support_info = coin_info.support_info(defs)
    mark_unsupported(support_info, defs.as_list())
    all_checks_passed = True

    print("Checking BTC-like coins...")
    if not check_btc(defs.bitcoin):
        all_checks_passed = False

    print("Checking Ethereum networks...")
    if not check_eth(defs.eth):
        all_checks_passed = False

    if not check_dups(buckets):
        all_checks_passed = False

    nontoken_dups = [coin for coin in defs.as_list() if "dup_key_nontoken" in coin]
    if nontoken_dups:
        nontoken_dup_str = ", ".join(
            highlight_key(coin, "red") for coin in nontoken_dups
        )
        print_log(logging.ERROR, "Non-token duplicate keys: " + nontoken_dup_str)
        all_checks_passed = False

    if icons:
        print("Checking icon files...")
        if not check_icons(defs.bitcoin):
            all_checks_passed = False

    if backend:
        print("Checking backend responses...")
        if not check_backends(defs.bitcoin):
            all_checks_passed = False

    print("Checking segwit fields...")
    if not check_segwit(defs.bitcoin):
        all_checks_passed = False

    print("Checking key uniformity...")
    for cointype, coinlist in defs.items():
        if cointype in ("erc20", "nem"):
            continue
        if not check_key_uniformity(coinlist):
            all_checks_passed = False

    print("Checking FIDO app definitions...")
    if not check_fido(coin_info.fido_info()):
        all_checks_passed = False

    if not all_checks_passed:
        print("Some checks failed.")
        sys.exit(1)
    else:
        print("Everything is OK.")


type_choice = click.Choice(["bitcoin", "eth", "erc20", "nem", "misc"])
device_choice = click.Choice(["connect", "suite", "T1B1", "T2T1", "T2B1"])


@cli.command()
# fmt: off
@click.option("-o", "--outfile", type=click.File(mode="w"), default="-")
@click.option("-s/-S", "--support/--no-support", default=True, help="Include support data for each coin")
@click.option("-p", "--pretty", is_flag=True, help="Generate nicely formatted JSON")
@click.option("-l", "--list", "flat_list", is_flag=True, help="Output a flat list of coins")
@click.option("-i", "--include", metavar="FIELD", multiple=True, help="Include only these fields (-i shortcut -i name)")
@click.option("-e", "--exclude", metavar="FIELD", multiple=True, help="Exclude these fields (-e blockchain_link)")
@click.option("-I", "--include-type", metavar="TYPE", multiple=True, type=type_choice, help="Include only these categories (-I bitcoin -I erc20)")
@click.option("-E", "--exclude-type", metavar="TYPE", multiple=True, type=type_choice, help="Exclude these categories (-E nem -E misc)")
@click.option("-f", "--filter", metavar="FIELD=FILTER", multiple=True, help="Include only coins that match a filter (-f taproot=true -f maintainer='*stick*')")
@click.option("-F", "--filter-exclude", metavar="FIELD=FILTER", multiple=True, help="Exclude coins that match a filter (-F 'blockbook=[]' -F 'slip44=*')")
@click.option("-t", "--exclude-tokens", is_flag=True, help="Exclude ERC20 tokens. Equivalent to '-E erc20'")
@click.option("-d", "--device-include", metavar="NAME", multiple=True, type=device_choice, help="Only include coins supported on these given devices (-d connect -d T1B1)")
@click.option("-D", "--device-exclude", metavar="NAME", multiple=True, type=device_choice, help="Only include coins not supported on these given devices (-D suite -D T2T1)")
# fmt: on
def dump(
    outfile: TextIO,
    support: bool,
    pretty: bool,
    flat_list: bool,
    include: tuple[str, ...],
    exclude: tuple[str, ...],
    include_type: tuple[str, ...],
    exclude_type: tuple[str, ...],
    filter: tuple[str, ...],
    filter_exclude: tuple[str, ...],
    exclude_tokens: bool,
    device_include: tuple[str, ...],
    device_exclude: tuple[str, ...],
) -> None:
    """Dump coin data in JSON format.

    By default prints to stdout, specify an output file with '-o file.json'.

    This file is structured the same as the internal data. That is, top-level object
    is a dict with keys: 'bitcoin', 'eth', 'erc20', 'nem' and 'misc'. Value for each
    key is a list of dicts, each describing a known coin.

    If '--list' is specified, the top-level object is instead a flat list of coins.

    \b
    Fields are category-specific, except for four common ones:
    - 'name' - human-readable name
    - 'shortcut' - currency symbol
    - 'key' - unique identifier, e.g., 'bitcoin:BTC'
    - 'support' - a dict with entries per known device

    To control the size and properties of the resulting file, you can specify whether
    or not you want pretty-printing and whether or not to include support data with
    each coin.

    You can specify which categories and which fields will be included or excluded.
    You cannot specify both include and exclude at the same time. Include is "stronger"
    than exclude, in that _only_ the specified fields are included.

    You can also specify filters, in the form '-f field=value' (or '-F' for inverse
    filter). Filter values are case-insensitive and support shell-style wildcards,
    so '-f name=bit*' finds all coins whose names start with "bit" or "Bit".

    Also devices can be used as filters. For example to find out which coins are
    supported in Suite and connect but not on Trezor 1, it is possible to say
    '-d suite -d connect -D T1B1'.
    """
    if exclude_tokens:
        exclude_type += ("erc20",)

    if include and exclude:
        raise click.ClickException(
            "You cannot specify --include and --exclude at the same time."
        )
    if include_type and exclude_type:
        raise click.ClickException(
            "You cannot specify --include-type and --exclude-type at the same time."
        )

    # getting initial info
    coins = coin_info.coin_info()
    support_info = coin_info.support_info(coins.as_list())

    # optionally adding support info
    if support:
        for category in coins.values():
            for coin in category:
                coin["support"] = support_info[coin["key"]]

    # filter types
    if include_type:
        coins_dict = {k: v for k, v in coins.items() if k in include_type}
    elif exclude_type:
        coins_dict = {k: v for k, v in coins.items() if k not in exclude_type}
    else:
        coins_dict = coins

    # filter individual coins
    include_filters = [f.split("=", maxsplit=1) for f in filter]
    exclude_filters = [f.split("=", maxsplit=1) for f in filter_exclude]

    # always exclude 'address_bytes', not encodable in JSON
    exclude += ("address_bytes",)

    def should_include_coin(coin: Coin) -> bool:
        for field, filter in include_filters:
            if field not in coin:
                return False
            if not fnmatch.fnmatch(str(coin[field]).lower(), filter.lower()):
                return False
        for field, filter in exclude_filters:
            if field not in coin:
                continue
            if fnmatch.fnmatch(str(coin[field]).lower(), filter.lower()):
                return False
        if device_include:
            is_supported_everywhere = all(
                support_info[coin["key"]].get(device) for device in device_include
            )
            if not is_supported_everywhere:
                return False
        if device_exclude:
            is_supported_somewhere = any(
                support_info[coin["key"]].get(device) for device in device_exclude
            )
            if is_supported_somewhere:
                return False
        return True

    def modify_coin(coin: Coin) -> Coin:
        if include:
            return cast(Coin, {k: v for k, v in coin.items() if k in include})
        else:
            return cast(Coin, {k: v for k, v in coin.items() if k not in exclude})

    for key, coinlist in coins_dict.items():
        coins_dict[key] = [modify_coin(c) for c in coinlist if should_include_coin(c)]

    # deciding the output structure
    if flat_list:
        output = sum(coins_dict.values(), [])
    else:
        output = coins_dict

    # dump the data - to stdout or to a file
    with outfile:
        indent = 4 if pretty else None
        json.dump(output, outfile, indent=indent, sort_keys=True)
        outfile.write("\n")


@cli.command()
# fmt: off
@click.argument("paths", type=click.Path(path_type=Path), metavar="[path]...", nargs=-1)
@click.option("-o", "--outfile", type=click.Path(dir_okay=False, writable=True, path_type=Path), help="Alternate output file")
@click.option("-v", "--verbose", is_flag=True, help="Print rendered file names")
@click.option("-b", "--bitcoin-only", is_flag=True, help="Accept only Bitcoin coins")
@click.option("-M", "--model-exclude", metavar="NAME", multiple=True, type=device_choice, help="Skip generation for this models (-M T1B1)")
# fmt: on
def render(
    paths: tuple[Path, ...],
    outfile: Path,
    verbose: bool,
    bitcoin_only: bool,
    model_exclude: tuple[str, ...],
) -> None:
    """Generate source code from Mako templates.

    For every "foo.bar.mako" filename passed, runs the template and
    saves the result as "foo.bar". For every directory name passed,
    processes all ".mako" files found in that directory.

    If `-o` is specified, renders a single file into the specified outfile.

    If no arguments are given, processes the current directory.
    """
    if not CAN_RENDER:
        raise click.ClickException("Please install 'mako' and 'munch'")

    if outfile and (len(paths) != 1 or not os.path.isfile(paths[0])):
        raise click.ClickException("Option -o can only be used with single input file")

    # prepare defs
    defs = coin_info.coin_info()
    defs["fido"] = coin_info.fido_info()
    support_info = coin_info.support_info(defs)

    if bitcoin_only:
        defs["bitcoin"] = [
            x
            for x in defs["bitcoin"]
            if x["coin_name"] in ("Bitcoin", "Testnet", "Regtest")
        ]

    # munch dicts - make them attribute-accessible
    for key, value in defs.items():
        defs[key] = [Munch(coin) for coin in value]
    for key, value in support_info.items():
        support_info[key] = Munch(value)

    def do_render(src: Path, dst: Path) -> None:
        models = coin_info.get_models()
        models = [m for m in models if m not in model_exclude]

        if verbose:
            click.echo(f"Rendering {src} => {dst.name}")
        render_file(src, dst, defs, support_info, models)

    # single in-out case
    if outfile:
        do_render(paths[0], outfile)
        return

    # find files in directories
    if not paths:
        paths = (Path(),)

    files: list[Path] = []
    for path in paths:
        if not path.exists():
            click.echo(f"Path {path} does not exist")
        elif path.is_dir():
            files.extend(path.glob("*.mako"))
        else:
            files.append(path)

    # render each file
    for file in files:
        if not file.suffix == ".mako":
            click.echo(f"File {file} does not end with .mako")
        else:
            do_render(file, file.parent / file.stem)


@cli.command()
# fmt: off
@click.option("-v", "--verbose", is_flag=True, help="Print timestamp and merkle root")
# fmt: on
def new_definitions(verbose: bool) -> None:
    """Update timestamp of external coin definitions."""
    assert requests is not None
    eth_defs = requests.get(DEFINITIONS_LATEST_URL).json()
    eth_defs_date = eth_defs["metadata"]["datetime"]
    if verbose:
        click.echo(
            f"Latest definitions from {eth_defs_date}: {eth_defs['metadata']['merkle_root']}"
        )
    eth_defs_date = datetime.datetime.fromisoformat(eth_defs_date)
    DEFINITIONS_TIMESTAMP_PATH.write_text(
        eth_defs_date.isoformat(timespec="seconds") + "\n"
    )


if __name__ == "__main__":
    cli()
