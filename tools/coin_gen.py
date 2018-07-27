#!/usr/bin/env python3
import io
import json
import re
import sys
import os
import glob

import click

import coin_defs

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
    from hashlib import sha256
    import ed25519
    from PIL import Image
    from trezorlib.protobuf import dump_message
    from coindef import CoinDef

    CAN_BUILD_DEFS = True
except ImportError:
    CAN_BUILD_DEFS = False


# ======= Jinja2 management ======


def c_str_filter(b):
    if b is None:
        return "NULL"

    def hexescape(c):
        return r"\x{:02x}".format(c)

    if isinstance(b, bytes):
        return '"' + "".join(map(hexescape, b)) + '"'
    else:
        return json.dumps(b)


def ascii_filter(s):
    return re.sub("[^ -\x7e]", "_", s)


MAKO_FILTERS = {"c_str": c_str_filter, "ascii": ascii_filter}


def render_file(filename, coins, support_info):
    """Opens `filename.j2`, renders the template and stores the result in `filename`."""
    template = mako.template.Template(filename=filename + ".mako")
    result = template.render(support_info=support_info, **coins, **MAKO_FILTERS)
    with open(filename, "w") as f:
        f.write(result)


# ====== validation functions ======


def check_support(defs, support_data):
    check_passed = True

    for key, support in support_data.items():
        errors = coin_defs.validate_support(support)
        if errors:
            check_passed = False
            print("ERR:", "invalid definition for", key)
            print("\n".join(errors))

    expected_coins = set(coin["key"] for coin in defs["coins"] + defs["misc"])

    # detect missing support info for expected
    for coin in expected_coins:
        if coin not in support_data:
            check_passed = False
            print("ERR: Missing support info for", coin)

    # detect non-matching support info
    coin_list = sum(defs.values(), [])
    coin_set = set(coin["key"] for coin in coin_list)
    for key in support_data:
        # detect non-matching support info
        if key not in coin_set:
            check_passed = False
            print("ERR: Support info found for unknown coin", key)

        # detect override - info only, doesn't fail check
        if key not in expected_coins:
            print("INFO: Override present for coin", key)

    return check_passed


def check_btc(coins):
    check_passed = True

    for coin in coins:
        errors = coin_defs.validate_btc(coin)
        if errors:
            check_passed = False
            print("ERR:", "invalid definition for", coin["name"])
            print("\n".join(errors))

    collisions = coin_defs.find_address_collisions(coins)
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
                j = requests.get(backend + "/block-index/0").json()
                if j["blockHash"] != genesis_block:
                    raise RuntimeError("genesis block mismatch")
            except Exception as e:
                print(e)
                check_passed = False
            else:
                print("OK")
    return check_passed


# ====== click command handlers ======


@click.group()
def cli():
    pass


@cli.command()
@click.option(
    "--backend-check/--no-backend-check",
    "-b",
    help="Also check blockbook/bitcore responses",
)
def check(backend_check):
    """Validate coin definitions.

    Checks that every btc-like coin is properly filled out, reports address collisions
    and missing support information.
    """
    if backend_check and requests is None:
        raise click.ClickException("You must install requests for backend check")

    defs = coin_defs.get_all()
    all_checks_passed = True

    print("Checking BTC-like coins...")
    if not check_btc(defs["coins"]):
        all_checks_passed = False

    print("Checking support data...")
    if not check_support(defs, coin_defs.get_support_data()):
        all_checks_passed = False

    if backend_check:
        print("Checking backend responses...")
        if not check_backends(defs["coins"]):
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
    defs = coin_defs.get_all()
    coins = defs["coins"]
    support_info = coin_defs.support_info(coins)
    by_name = {}
    for coin in coins:
        coin["support"] = support_info[coin["key"]]
        by_name[coin["name"]] = coin

    with outfile:
        json.dump(by_name, outfile, indent=4, sort_keys=True)


@cli.command()
@click.argument("paths", metavar="[path]...", nargs=-1)
def render(paths):
    """Generate source code from Jinja2 templates.

    For every "foo.bar.j2" filename passed, runs the template and
    saves the result as "foo.bar".

    For every directory name passed, processes all ".j2" files found
    in that directory.

    If no arguments are given, processes the current directory.
    """
    if not CAN_RENDER:
        raise click.ClickException("Please install 'mako' and 'munch'")

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

    defs = coin_defs.get_all()
    all_coins = sum(defs.values(), [])
    versions = coin_defs.latest_releases()
    support_info = coin_defs.support_info(all_coins, erc20_versions=versions)

    # munch dicts - make them attribute-accessable
    for key, value in defs.items():
        defs[key] = [Munch(coin) for coin in value]
    for key, value in support_info.items():
        support_info[key] = Munch(value)

    for file in files:
        if not file.endswith(".mako"):
            click.echo("File {} does not end with .mako".format(file))
        else:
            target = file[: -len(".mako")]
            click.echo("Rendering {} => {}".format(file, target))
            try:
                render_file(target, defs, support_info)
            except Exception as e:
                click.echo("Error occured: {}".format(e))
                raise


if __name__ == "__main__":
    cli()
