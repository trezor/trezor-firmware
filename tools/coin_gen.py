#!/usr/bin/env python3
import io
import json
import re
import sys
import os
import glob
import binascii
import struct
import zlib
from hashlib import sha256

import click

import coin_info
from coindef import CoinDef


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


def check_btc(coins):
    check_passed = True

    for coin in coins:
        errors = coin_info.validate_btc(coin)
        if errors:
            check_passed = False
            print("ERR:", "invalid definition for", coin["name"])
            print("\n".join(errors))

    collisions = coin_info.find_address_collisions(coins)
    # warning only
    for key, dups in collisions.items():
        if dups:
            print("WARN: collisions found in", key)
            for k, v in dups.items():
                print("-", k, ":", ", ".join(map(str, v)))

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
def cli():
    pass


@cli.command()
@click.option(
    "--missing-support/--no-missing-support",
    "-s",
    default=False,
    help="Fail if support info for a coin is missing",
)
@click.option(
    "--backend/--no-backend",
    "-b",
    default=False,
    help="Check blockbook/bitcore responses",
)
@click.option("--icons/--no-icons", default=True, help="Check icon files")
def check(missing_support, backend, icons):
    """Validate coin definitions.

    Checks that every btc-like coin is properly filled out, reports address collisions
    and missing support information.
    """
    if backend and requests is None:
        raise click.ClickException("You must install requests for backend check")

    if icons and not CAN_BUILD_DEFS:
        raise click.ClickException("Missing requirements for icon check")

    defs = coin_info.get_all()
    all_checks_passed = True

    print("Checking BTC-like coins...")
    if not check_btc(defs.coins):
        all_checks_passed = False

    # XXX support.py is responsible for checking support data
    # print("Checking support data...")
    # support_data = coin_info.get_support_data()
    # if not check_support(defs, support_data, fail_missing=missing_support):
    #     all_checks_passed = False

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
@click.argument("paths", metavar="[path]...", nargs=-1)
@click.option("-o", "--outfile", type=click.File("w"), help="Alternate output file")
@click.option("-v", "--verbose", is_flag=True, help="Print rendered file names")
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
