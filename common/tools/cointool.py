#!/usr/bin/env python3
import fnmatch
import glob
import io
import json
import logging
import os
import re
import struct
import sys
import zlib
from collections import defaultdict
from hashlib import sha256

import click

import coin_info
from coindef import CoinDef

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
    import ed25519
    from PIL import Image
    from trezorlib import protobuf

    CAN_BUILD_DEFS = True
except ImportError:
    CAN_BUILD_DEFS = False


# ======= Crayon colors ======
USE_COLORS = False


def crayon(color, string, bold=False, dim=False):
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


def print_log(level, *args, **kwargs):
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


def c_str_filter(b):
    if b is None:
        return "NULL"

    def hexescape(c):
        return r"\x{:02x}".format(c)

    if isinstance(b, bytes):
        return '"' + "".join(map(hexescape, b)) + '"'
    else:
        return json.dumps(b)


def black_repr_filter(val):
    if isinstance(val, str):
        if '"' in val:
            return repr(val)
        else:
            return c_str_filter(val)
    elif isinstance(val, bytes):
        return "b" + c_str_filter(val)
    else:
        return repr(val)


def ascii_filter(s):
    return re.sub("[^ -\x7e]", "_", s)


def make_support_filter(support_info):
    def supported_on(device, coins):
        for coin in coins:
            supp = support_info[coin.key].get(device)
            if not supp:
                continue
            if coin_info.is_token(coin) or supp != "soon":
                yield coin

    return supported_on


MAKO_FILTERS = {
    "c_str": c_str_filter,
    "ascii": ascii_filter,
    "black_repr": black_repr_filter,
}


def render_file(src, dst, coins, support_info):
    """Renders `src` template into `dst`.

    `src` is a filename, `dst` is an open file object.
    """
    template = mako.template.Template(filename=src)
    result = template.render(
        support_info=support_info,
        supported_on=make_support_filter(support_info),
        **coins,
        **MAKO_FILTERS,
    )
    dst.write(result)


# ====== validation functions ======


def mark_unsupported(support_info, coins):
    for coin in coins:
        key = coin["key"]
        # checking for explicit False because None means unknown
        coin["unsupported"] = all(v is False for v in support_info[key].values())


def highlight_key(coin, color):
    """Return a colorful string where the SYMBOL part is bold."""
    keylist = coin["key"].split(":")
    if keylist[-1].isdigit():
        keylist[-2] = crayon(color, keylist[-2], bold=True)
    else:
        keylist[-1] = crayon(color, keylist[-1], bold=True)
    key = crayon(color, ":".join(keylist))
    name = crayon(None, "({})".format(coin["name"]), dim=True)
    return "{} {}".format(key, name)


def find_collisions(coins, field):
    """Detects collisions in a given field. Returns buckets of colliding coins."""
    collisions = defaultdict(list)
    for coin in coins:
        values = coin[field]
        if not isinstance(values, list):
            values = [values]
        for value in values:
            collisions[value].append(coin)
    return {k: v for k, v in collisions.items() if len(v) > 1}


def check_eth(coins):
    check_passed = True
    chains = find_collisions(coins, "chain")
    for key, bucket in chains.items():
        bucket_str = ", ".join(
            "{} ({})".format(coin["key"], coin["name"]) for coin in bucket
        )
        chain_name_str = "colliding chain name " + crayon(None, key, bold=True) + ":"
        print_log(logging.ERROR, chain_name_str, bucket_str)
        check_passed = False
    for coin in coins:
        icon_file = coin["chain"] + ".png"
        try:
            icon = Image.open(os.path.join(coin_info.DEFS_DIR, "ethereum", icon_file))
        except Exception:
            print(coin["key"], ": failed to open icon file", icon_file)
            check_passed = False
            continue

        if icon.size != (128, 128) or icon.mode != "RGBA":
            print(coin["key"], ": bad icon format (must be RGBA 128x128)")
            check_passed = False
    return check_passed


def check_btc(coins):
    check_passed = True

    # validate individual coin data
    for coin in coins:
        errors = coin_info.validate_btc(coin)
        if errors:
            check_passed = False
            print_log(logging.ERROR, "invalid definition for", coin["name"])
            print("\n".join(errors))

    def collision_str(bucket):
        """Generate a colorful string out of a bucket of colliding coins."""
        coin_strings = []
        for coin in bucket:
            name = coin["name"]
            prefix = ""
            if name.endswith("Testnet") or name.endswith("Regtest"):
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

    def print_collision_buckets(buckets, prefix, maxlevel=logging.ERROR, strict=False):
        """Intelligently print collision buckets.

        For each bucket, if there are any collision with a mainnet, print it.
        If the collision is with unsupported networks or testnets, it's just INFO.
        If the collision is with supported mainnets, it's WARNING.
        If the collision with any supported network includes Bitcoin, it's an ERROR.
        """
        failed = False
        for key, bucket in buckets.items():
            mainnets = [
                c
                for c in bucket
                if not c["name"].endswith("Testnet")
                and not c["name"].endswith("Regtest")
            ]

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
                print_log(level, "{} {}:".format(prefix, key), collision_str(bucket))

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


def check_dups(buckets, print_at_level=logging.WARNING):
    """Analyze and pretty-print results of `coin_info.mark_duplicate_shortcuts`.

    `print_at_level` can be one of logging levels.

    The results are buckets of colliding symbols.
    If the collision is only between ERC20 tokens, it's DEBUG.
    If the collision includes one non-token, it's INFO.
    If the collision includes more than one non-token, it's ERROR and printed always.
    """

    def coin_str(coin):
        """Colorize coins. Tokens are cyan, nontokens are red. Coins that are NOT
        marked duplicate get a green asterisk.
        """
        prefix = ""
        if coin["unsupported"]:
            color = "grey"
            prefix = crayon("blue", "(X)", bold=True)
        elif coin_info.is_token(coin):
            color = "cyan"
        else:
            color = "red"

        if not coin.get("duplicate"):
            prefix = crayon("green", "*", bold=True) + prefix

        highlighted = highlight_key(coin, color)
        return "{}{}".format(prefix, highlighted)

    check_passed = True

    for symbol in sorted(buckets.keys()):
        bucket = buckets[symbol]
        if not bucket:
            continue

        supported = [coin for coin in bucket if not coin["unsupported"]]
        nontokens = [coin for coin in bucket if not coin_info.is_token(coin)]
        cleared = not any(coin.get("duplicate") for coin in bucket)

        # string generation
        dup_str = ", ".join(coin_str(coin) for coin in bucket)
        if len(nontokens) > 1:
            # Two or more colliding nontokens. This is always fatal.
            # XXX consider allowing two nontokens as long as only one is supported?
            level = logging.ERROR
            check_passed = False
        elif len(supported) > 1:
            # more than one supported coin in bucket
            if cleared:
                # some previous step has explicitly marked them as non-duplicate
                level = logging.INFO
            else:
                # at most 1 non-token - we tenatively allow token collisions
                # when explicitly marked as supported
                level = logging.WARNING
        else:
            # At most 1 supported coin, at most 1 non-token. This is informational only.
            level = logging.DEBUG

        # deciding whether to print
        if level < print_at_level:
            continue

        if symbol == "_override":
            print_log(level, "force-set duplicates:", dup_str)
        else:
            print_log(level, "duplicate symbol {}:".format(symbol.upper()), dup_str)

    return check_passed


def check_backends(coins):
    check_passed = True
    for coin in coins:
        genesis_block = coin.get("hash_genesis_block")
        if not genesis_block:
            continue
        backends = coin.get("blockbook", []) + coin.get("bitcore", [])
        for backend in backends:
            print("checking", backend, "... ", end="", flush=True)
            try:
                j = requests.get(backend + "/api/block-index/0").json()
                if j["blockHash"] != genesis_block:
                    raise RuntimeError("genesis block mismatch")
            except Exception as e:
                print(e)
                check_passed = False
            else:
                print("OK")
    return check_passed


def check_icons(coins):
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


IGNORE_NONUNIFORM_KEYS = frozenset(("unsupported", "duplicate"))


def check_key_uniformity(coins):
    keysets = defaultdict(list)
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
            print_log(
                logging.ERROR, "coin {} has missing keys: {}".format(key, missing)
            )
        additional = ", ".join(keyset - reference_keyset)
        if additional:
            print_log(
                logging.ERROR,
                "coin {} has superfluous keys: {}".format(key, additional),
            )

    return False


def check_segwit(coins):
    for coin in coins:
        segwit = coin["segwit"]
        segwit_fields = [
            "bech32_prefix",
            "xpub_magic_segwit_native",
            "xpub_magic_segwit_p2sh",
        ]
        if segwit:
            for field in segwit_fields:
                if coin[field] is None:
                    print_log(
                        logging.ERROR,
                        coin["name"],
                        "segwit is True => %s should be set" % field,
                    )
                    return False
        else:
            for field in segwit_fields:
                if coin[field] is not None:
                    print_log(
                        logging.ERROR,
                        coin["name"],
                        "segwit is True => %s should NOT be set" % field,
                    )
                    return False
    return True


FIDO_KNOWN_KEYS = frozenset(
    (
        "key",
        "u2f",
        "webauthn",
        "label",
        "use_sign_count",
        "use_self_attestation",
        "no_icon",
        "icon",
    )
)


def check_fido(apps):
    check_passed = True

    uf2_hashes = find_collisions((a for a in apps if "u2f" in a), "u2f")
    for key, bucket in uf2_hashes.items():
        bucket_str = ", ".join(app["key"] for app in bucket)
        u2f_hash_str = "colliding U2F hash " + crayon(None, key, bold=True) + ":"
        print_log(logging.ERROR, u2f_hash_str, bucket_str)
        check_passed = False

    webauthn_domains = find_collisions((a for a in apps if "webauthn" in a), "webauthn")
    for key, bucket in webauthn_domains.items():
        bucket_str = ", ".join(app["key"] for app in bucket)
        webauthn_str = "colliding WebAuthn domain " + crayon(None, key, bold=True) + ":"
        print_log(logging.ERROR, webauthn_str, bucket_str)
        check_passed = False

    for app in apps:
        if "label" not in app:
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


# ====== coindefs generators ======


def convert_icon(icon):
    """Convert PIL icon to TOIF format"""
    # TODO: move this to python-trezor at some point
    DIM = 32
    icon = icon.resize((DIM, DIM), Image.LANCZOS)
    # remove alpha channel, replace with black
    bg = Image.new("RGBA", icon.size, (0, 0, 0, 255))
    icon = Image.alpha_composite(bg, icon)
    # process pixels
    pix = icon.load()
    data = bytes()
    for y in range(DIM):
        for x in range(DIM):
            r, g, b, _ = pix[x, y]
            c = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)
            data += struct.pack(">H", c)
    z = zlib.compressobj(level=9, wbits=10)
    zdata = z.compress(data) + z.flush()
    zdata = zdata[2:-4]  # strip header and checksum
    return zdata


def coindef_from_dict(coin):
    proto = CoinDef()
    for fname, _, fflags in CoinDef.FIELDS.values():
        val = coin.get(fname)
        if val is None and fflags & protobuf.FLAG_REPEATED:
            val = []
        elif fname == "signed_message_header":
            val = val.encode()
        elif fname == "hash_genesis_block":
            val = bytes.fromhex(val)
        setattr(proto, fname, val)

    return proto


def serialize_coindef(proto, icon):
    proto.icon = icon
    buf = io.BytesIO()
    protobuf.dump_message(buf, proto)
    return buf.getvalue()


def sign(data):
    h = sha256(data).digest()
    sign_key = ed25519.SigningKey(b"A" * 32)
    return sign_key.sign(h)


# ====== click command handlers ======


@click.group()
@click.option(
    "--colors/--no-colors",
    "-c/-C",
    default=sys.stdout.isatty(),
    help="Force colored output on/off",
)
def cli(colors):
    global USE_COLORS
    USE_COLORS = colors


@cli.command()
# fmt: off
@click.option("--backend/--no-backend", "-b", default=False, help="Check blockbook/bitcore responses")
@click.option("--icons/--no-icons", default=True, help="Check icon files")
@click.option("-d", "--show-duplicates", type=click.Choice(("all", "nontoken", "errors")), default="errors", help="How much information about duplicate shortcuts should be shown.")
# fmt: on
def check(backend, icons, show_duplicates):
    """Validate coin definitions.

    Checks that every btc-like coin is properly filled out, reports duplicate symbols,
    missing or invalid icons, backend responses, and uniform key information --
    i.e., that all coins of the same type have the same fields in their JSON data.

    Uniformity check ignores NEM mosaics and ERC20 tokens, where non-uniformity is
    expected.

    The `--show-duplicates` option can be set to:

    - all: all shortcut collisions are shown, including colliding ERC20 tokens

    - nontoken: only collisions that affect non-ERC20 coins are shown

    - errors: only collisions between non-ERC20 tokens are shown. This is the default,
    as a collision between two or more non-ERC20 tokens is an error.

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

    if icons and not CAN_BUILD_DEFS:
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

    if show_duplicates == "all":
        dup_level = logging.DEBUG
    elif show_duplicates == "nontoken":
        dup_level = logging.INFO
    else:
        dup_level = logging.WARNING
    print("Checking unexpected duplicates...")
    if not check_dups(buckets, dup_level):
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


@cli.command()
# fmt: off
@click.option("-o", "--outfile", type=click.File(mode="w"), default="-")
@click.option("-s/-S", "--support/--no-support", default=True, help="Include support data for each coin")
@click.option("-p", "--pretty", is_flag=True, help="Generate nicely formatted JSON")
@click.option("-l", "--list", "flat_list", is_flag=True, help="Output a flat list of coins")
@click.option("-i", "--include", metavar="FIELD", multiple=True, help="Include only these fields")
@click.option("-e", "--exclude", metavar="FIELD", multiple=True, help="Exclude these fields")
@click.option("-I", "--include-type", metavar="TYPE", multiple=True, help="Include only these categories")
@click.option("-E", "--exclude-type", metavar="TYPE", multiple=True, help="Exclude these categories")
@click.option("-f", "--filter", metavar="FIELD=FILTER", multiple=True, help="Include only coins that match a filter")
@click.option("-F", "--filter-exclude", metavar="FIELD=FILTER", multiple=True, help="Exclude coins that match a filter")
@click.option("-t", "--exclude-tokens", is_flag=True, help="Exclude ERC20 tokens. Equivalent to '-E erc20'")
@click.option("-d", "--device", metavar="NAME", help="Only include coins supported on a given device")
# fmt: on
def dump(
    outfile,
    support,
    pretty,
    flat_list,
    include,
    exclude,
    include_type,
    exclude_type,
    filter,
    filter_exclude,
    exclude_tokens,
    device,
):
    """Dump coin data in JSON format.

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
    """
    if exclude_tokens:
        exclude_type = ("erc20",)

    if include and exclude:
        raise click.ClickException(
            "You cannot specify --include and --exclude at the same time."
        )
    if include_type and exclude_type:
        raise click.ClickException(
            "You cannot specify --include-type and --exclude-type at the same time."
        )

    coins = coin_info.coin_info()
    support_info = coin_info.support_info(coins.as_list())

    if support:
        for category in coins.values():
            for coin in category:
                coin["support"] = support_info[coin["key"]]

    # filter types
    if include_type:
        coins_dict = {k: v for k, v in coins.items() if k in include_type}
    else:
        coins_dict = {k: v for k, v in coins.items() if k not in exclude_type}

    # filter individual coins
    include_filters = [f.split("=", maxsplit=1) for f in filter]
    exclude_filters = [f.split("=", maxsplit=1) for f in filter_exclude]

    # always exclude 'address_bytes', not encodable in JSON
    exclude += ("address_bytes",)

    def should_include_coin(coin):
        for field, filter in include_filters:
            filter = filter.lower()
            if field not in coin:
                return False
            if not fnmatch.fnmatch(str(coin[field]).lower(), filter):
                return False
        for field, filter in exclude_filters:
            filter = filter.lower()
            if field not in coin:
                continue
            if fnmatch.fnmatch(str(coin[field]).lower(), filter):
                return False
        if device:
            is_supported = support_info[coin["key"]].get(device, None)
            if not is_supported:
                return False
        return True

    def modify_coin(coin):
        if include:
            return {k: v for k, v in coin.items() if k in include}
        else:
            return {k: v for k, v in coin.items() if k not in exclude}

    for key, coinlist in coins_dict.items():
        coins_dict[key] = [modify_coin(c) for c in coinlist if should_include_coin(c)]

    if flat_list:
        output = sum(coins_dict.values(), [])
    else:
        output = coins_dict

    with outfile:
        indent = 4 if pretty else None
        json.dump(output, outfile, indent=indent, sort_keys=True)
        outfile.write("\n")


@cli.command()
@click.option("-o", "--outfile", type=click.File(mode="w"), default="./coindefs.json")
def coindefs(outfile):
    """Generate signed coin definitions for python-trezor and others

    This is currently unused but should enable us to add new coins without having to
    update firmware.
    """
    coins = coin_info.coin_info().bitcoin
    coindefs = {}
    for coin in coins:
        key = coin["key"]
        icon = Image.open(coin["icon"])
        ser = serialize_coindef(coindef_from_dict(coin), convert_icon(icon))
        sig = sign(ser)
        definition = (sig + ser).hex()
        coindefs[key] = definition

    with outfile:
        json.dump(coindefs, outfile, indent=4, sort_keys=True)
        outfile.write("\n")


@cli.command()
# fmt: off
@click.argument("paths", metavar="[path]...", nargs=-1)
@click.option("-o", "--outfile", type=click.File("w"), help="Alternate output file")
@click.option("-v", "--verbose", is_flag=True, help="Print rendered file names")
@click.option("-b", "--bitcoin-only", is_flag=True, help="Accept only Bitcoin coins")
# fmt: on
def render(paths, outfile, verbose, bitcoin_only):
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

    def do_render(src, dst):
        if verbose:
            click.echo("Rendering {} => {}".format(src, dst))
        render_file(src, dst, defs, support_info)

    # single in-out case
    if outfile:
        do_render(paths[0], outfile)
        return

    # find files in directories
    if not paths:
        paths = ["."]

    files = []
    for path in paths:
        if not os.path.exists(path):
            click.echo("Path {} does not exist".format(path))
        elif os.path.isdir(path):
            files += glob.glob(os.path.join(path, "*.mako"))
        else:
            files.append(path)

    # render each file
    for file in files:
        if not file.endswith(".mako"):
            click.echo("File {} does not end with .mako".format(file))
        else:
            target = file[: -len(".mako")]
            with open(target, "w") as dst:
                do_render(file, dst)


if __name__ == "__main__":
    cli()
