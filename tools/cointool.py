#!/usr/bin/env python3
import io
import json
import logging
import re
import sys
import os
import glob
import binascii
import struct
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
            if support_info[coin.key].get(device):
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


def highlight_key(coin, color):
    keylist = coin["key"].split(":")
    if keylist[-1].isdigit():
        keylist[-2] = crayon(color, keylist[-2], bold=True)
    else:
        keylist[-1] = crayon(color, keylist[-1], bold=True)
    key = crayon(color, ":".join(keylist))
    name = crayon(None, f"({coin['name']})", dim=True)
    return f"{key} {name}"


def find_address_collisions(coins, field):
    """Detects collisions in a given field. Returns buckets of colliding coins."""
    collisions = defaultdict(list)
    for coin in coins:
        value = coin[field]
        collisions[value].append(coin)
    return {k: v for k, v in collisions.items() if len(v) > 1}


def check_btc(coins):
    check_passed = True
    support_infos = coin_info.support_info(coins)

    for coin in coins:
        errors = coin_info.validate_btc(coin)
        if errors:
            check_passed = False
            print_log(logging.ERROR, "invalid definition for", coin["name"])
            print("\n".join(errors))

    def collision_str(bucket):
        coin_strings = []
        for coin in bucket:
            name = coin["name"]
            prefix = ""
            if name.endswith("Testnet"):
                color = "green"
            elif name == "Bitcoin":
                color = "red"
            elif coin.get("unsupported"):
                color = "grey"
                prefix = crayon("blue", "(X)", bold=True)
            else:
                color = "blue"
            hl = highlight_key(coin, color)
            coin_strings.append(prefix + hl)
        return ", ".join(coin_strings)

    def print_collision_buckets(buckets, prefix):
        failed = False
        for key, bucket in buckets.items():
            mainnets = [c for c in bucket if not c["name"].endswith("Testnet")]

            have_bitcoin = False
            for coin in mainnets:
                if coin["name"] == "Bitcoin":
                    have_bitcoin = True
                if all(v is None for k,v in support_infos[coin["key"]].items()):
                    coin["unsupported"] = True

            supported_mainnets = [c for c in mainnets if not c.get("unsupported")]
            supported_networks = [c for c in bucket if not c.get("unsupported")]

            if len(mainnets) > 1:
                if have_bitcoin and len(supported_networks) > 1:
                    # ANY collision with Bitcoin is bad
                    level = logging.ERROR
                    failed = True
                elif len(supported_mainnets) > 1:
                    # collision between supported networks is still pretty bad
                    level = logging.WARNING
                else:
                    # collision between some unsupported networks is OK
                    level = logging.INFO
                print_log(level, f"prefix {key}:", collision_str(bucket))

        return failed

    # slip44 collisions
    print("Checking SLIP44 prefix collisions...")
    slip44 = find_address_collisions(coins, "slip44")
    if print_collision_buckets(slip44, "key"):
        check_passed = False

    nocashaddr = [coin for coin in coins if not coin.get("cashaddr_prefix")]
    
    print("Checking address_type collisions...")
    address_type = find_address_collisions(nocashaddr, "address_type")
    if print_collision_buckets(address_type, "address type"):
        check_passed = False

    print("Checking address_type_p2sh collisions...")
    address_type_p2sh = find_address_collisions(nocashaddr, "address_type_p2sh")
    # we ignore failed checks on P2SH, because reasons
    print_collision_buckets(address_type_p2sh, "address type")

    return check_passed


def check_dups(buckets, show_tok_notok, show_erc20):
    def coin_str(coin):
        if coin_info.is_token(coin):
            color = "cyan"
        else:
            color = "red"
        highlighted = highlight_key(coin, color)
        if not coin.get("duplicate"):
            prefix = crayon("green", "*", bold=True)
        else:
            prefix = ""
        return f"{prefix}{highlighted}"

    check_passed = True

    for symbol in sorted(buckets.keys()):
        bucket = buckets[symbol]
        if not bucket:
            continue

        nontokens = [coin for coin in bucket if not coin_info.is_token(coin)]

        # string generation
        dup_str = ", ".join(coin_str(coin) for coin in bucket)
        if not nontokens:
            level = logging.DEBUG
        elif len(nontokens) == 1:
            level = logging.INFO
        else:
            level = logging.ERROR
            check_passed = False

        # deciding whether to print
        if not nontokens and not show_erc20:
            continue
        if len(nontokens) == 1 and not show_tok_notok:
            continue

        if symbol == "_override":
            print_log(level, "force-set duplicates:", dup_str)
        else:
            print_log(level, f"duplicate symbol {symbol}:", dup_str)

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
            val = val.encode("utf-8")
        elif fname == "hash_genesis_block":
            val = binascii.unhexlify(val)
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
@click.option("--missing-support/--no-missing-support", "-s", default=False, help="Fail if support info for a coin is missing")
@click.option("--backend/--no-backend", "-b", default=False, help="Check blockbook/bitcore responses")
@click.option("--icons/--no-icons", default=True, help="Check icon files")
@click.option("-d", "--show-duplicates", type=click.Choice(("all", "nontoken", "errors")),
    default="errors", help="How much information about duplicate shortcuts should be shown.")
# fmt: on
def check(missing_support, backend, icons, show_duplicates):
    """Validate coin definitions.

    Checks that every btc-like coin is properly filled out, reports address collisions
    and missing support information.

    The `--show-duplicates` option can be set to:
    * all: all shortcut collisions are shown, including colliding ERC20 tokens
    * nontoken: only collisions that affect non-ERC20 coins are shown
    * errors: only collisions between non-ERC20 tokens are shown. This is the default,
      as a collision between two or more non-ERC20 tokens is an error.

    In the output, duplicate ERC tokens will be shown in cyan; duplicate non-tokens
    in red. An asterisk (*) next to symbol name means that even though it was detected
    as duplicate, it is still included in results.

    The code checks that SLIP44 numbers don't collide between different mainnets
    (testnet collisions are allowed), that `address_prefix` doesn't collide with
    Bitcoin (other collisions are reported as warnings). `address_prefix_p2sh`
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

    defs = coin_info.get_all(deduplicate=False)
    buckets = coin_info.mark_duplicate_shortcuts(defs.as_list())
    all_checks_passed = True

    print("Checking BTC-like coins...")
    if not check_btc(defs.coins):
        all_checks_passed = False

    if show_duplicates == "all":
        show_tok_notok = True
        show_erc20 = True
    elif show_duplicates == "nontoken":
        show_tok_notok = True
        show_erc20 = False
    else:
        show_tok_notok = False
        show_erc20 = False
    print("Checking unexpected duplicates...")
    if not check_dups(buckets, show_tok_notok, show_erc20):
        all_checks_passed = False

    if icons:
        print("Checking icon files...")
        if not check_icons(defs.coins):
            all_checks_passed = False

    if backend:
        print("Checking backend responses...")
        if not check_backends(defs.coins):
            all_checks_passed = False

    if not all_checks_passed:
        print("Some checks failed.")
        sys.exit(1)
    else:
        print("Everything is OK.")


@cli.command()
@click.option("-o", "--outfile", type=click.File(mode="w"), default="./coins.json")
def coins_json(outfile):
    """Generate coins.json for consumption in python-trezor and Connect/Wallet"""
    coins = coin_info.get_all().coins
    support_info = coin_info.support_info(coins)
    by_name = {}
    for coin in coins:
        coin["support"] = support_info[coin["key"]]
        by_name[coin["name"]] = coin

    with outfile:
        json.dump(by_name, outfile, indent=4, sort_keys=True)
        outfile.write("\n")


@cli.command()
@click.option("-o", "--outfile", type=click.File(mode="w"), default="./coindefs.json")
def coindefs(outfile):
    """Generate signed coin definitions for python-trezor and others

    This is currently unused but should enable us to add new coins without having to
    update firmware.
    """
    coins = coin_info.get_all().coins
    coindefs = {}
    for coin in coins:
        key = coin["key"]
        icon = Image.open(coin["icon"])
        ser = serialize_coindef(coindef_from_dict(coin), convert_icon(icon))
        sig = sign(ser)
        definition = binascii.hexlify(sig + ser).decode("ascii")
        coindefs[key] = definition

    with outfile:
        json.dump(coindefs, outfile, indent=4, sort_keys=True)
        outfile.write("\n")


@cli.command()
# fmt: off
@click.argument("paths", metavar="[path]...", nargs=-1)
@click.option("-o", "--outfile", type=click.File("w"), help="Alternate output file")
@click.option("-v", "--verbose", is_flag=True, help="Print rendered file names")
# fmt: on
def render(paths, outfile, verbose):
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
    defs = coin_info.get_all()
    support_info = coin_info.support_info(defs)

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
