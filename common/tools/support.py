#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys

import click

import coin_info

SUPPORT_INFO = coin_info.get_support_data()
MODELS = coin_info.get_models()

VERSION_RE = re.compile(r"\d+.\d+.\d+")

ERC20_DUPLICATE_KEY = "(AUTO) duplicate key"


def write_support_info():
    with open(os.path.join(coin_info.DEFS_DIR, "support.json"), "w") as f:
        json.dump(SUPPORT_INFO, f, indent=2, sort_keys=True)
        f.write("\n")


def support_dicts(device):
    return SUPPORT_INFO[device]["supported"], SUPPORT_INFO[device]["unsupported"]


def all_support_dicts():
    for device in SUPPORT_INFO:
        yield (device, *support_dicts(device))


def clear_support(device, key):
    supported, unsupported = support_dicts(device)
    supported.pop(key, None)
    unsupported.pop(key, None)


def support_setdefault(device, key, value, reason=None):
    """Set value only if no other value is set"""
    supported, unsupported = support_dicts(device)
    if value is not False and key not in unsupported:
        supported.setdefault(key, value)

    if value is False:
        if reason is None:
            raise ValueError("reason must be given for unsupported keys")
        if key not in supported:
            unsupported[key] = reason


def set_supported(device, key, value):
    clear_support(device, key)
    supported, _ = support_dicts(device)
    supported[key] = value


def set_unsupported(device, key, value):
    clear_support(device, key)
    _, unsupported = support_dicts(device)
    unsupported[key] = value


def print_support(coin):
    def support_value(where, key):
        if "supported" in where and key in where["supported"]:
            val = where["supported"][key]
            if val is True:
                return "YES"
            elif VERSION_RE.match(val):
                return f"YES since {val}"
            else:
                return f"BAD VALUE {val}"
        elif "unsupported" in where and key in where["unsupported"]:
            val = where["unsupported"][key]
            return f"NO (reason: {val})"
        else:
            return "support info missing"

    key, name, shortcut = coin["key"], coin["name"], coin["shortcut"]
    print(f"{key} - {name} ({shortcut})")
    if coin.get("duplicate"):
        print(" * DUPLICATE SYMBOL")
    for dev, where in SUPPORT_INFO.items():
        print(" *", dev, ":", support_value(where, key))


# ====== validation functions ====== #


def check_support_values():
    def _check_value_version_soon(value):
        if not isinstance(value, str):
            raise ValueError(f"non-str value: {value}")

        if not VERSION_RE.match(value):
            raise ValueError(f"expected version, found '{value}'")

    errors = []
    for device, values in SUPPORT_INFO.items():
        supported = values.get("supported")
        unsupported = values.get("unsupported")

        if not isinstance(supported, dict):
            errors.append(f"Missing 'supported' dict for {device}")
        else:
            for key, value in supported.items():
                try:
                    _check_value_version_soon(value)
                    if key in unsupported:
                        raise ValueError(f"{key} is both supported and unsupported")

                except Exception as e:
                    errors.append(f"{device}.supported.{key}: {e}")

        if not isinstance(unsupported, dict):
            errors.append(f"Missing 'supported' dict for {device}")
        else:
            for key, value in unsupported.items():
                if not isinstance(value, str) or not value:
                    errors.append(f"{device}.unsupported.{key}: missing reason")

    return errors


def find_unsupported_coins(coins_dict):
    result = {}
    for device in MODELS:
        supported, unsupported = support_dicts(device)
        support_set = set(supported.keys())
        support_set.update(unsupported.keys())

        result[device] = []
        for key, coin in coins_dict.items():
            if key not in support_set:
                result[device].append(coin)

    return result


def find_orphaned_support_keys(coins_dict):
    orphans = set()
    for _, supported, unsupported in all_support_dicts():
        orphans.update(key for key in supported if key not in coins_dict)
        orphans.update(key for key in unsupported if key not in coins_dict)

    return orphans


@click.group()
def cli():
    pass


@cli.command()
@click.option("-n", "--dry-run", is_flag=True, help="Do not write changes")
def fix(dry_run):
    """Fix expected problems.

    Currently only prunes orphaned keys.
    """
    all_coins = coin_info.coin_info()
    coins_dict = all_coins.as_dict()

    orphaned = find_orphaned_support_keys(coins_dict)
    for orphan in orphaned:
        print(f"pruning orphan {orphan}")
        for device in SUPPORT_INFO:
            clear_support(device, orphan)

    if not dry_run:
        write_support_info()


@cli.command()
# fmt: off
@click.option("-m", "--ignore-missing", is_flag=True, help="Do not fail on missing supportinfo")
# fmt: on
def check(ignore_missing):
    """Check validity of support information.

    Ensures that `support.json` data is well formed, there are no keys without
    corresponding coins, and there are no coins without corresponding keys.

    If `--ignore-missing` is specified, the check will display coins with missing
    support info, but will not fail when missing coins are found. This is
    useful in Travis.
    """
    all_coins = coin_info.coin_info()
    coins_dict = all_coins.as_dict()
    checks_ok = True

    errors = check_support_values()
    if errors:
        for error in errors:
            print(error)
        checks_ok = False

    orphaned = find_orphaned_support_keys(coins_dict)
    for orphan in orphaned:
        print(f"orphaned key {orphan}")
        checks_ok = False

    missing = find_unsupported_coins(coins_dict)
    for device, values in missing.items():
        if values:
            if not ignore_missing:
                checks_ok = False
            print(f"Device {device} has missing support infos:")
            for coin in values:
                print(f"{coin['key']} - {coin['name']}")

    if not checks_ok:
        print("Some checks have failed")
        sys.exit(1)


@cli.command()
# fmt: off
@click.option("-r", '--releases', multiple=True, type=str, help='Key-value pairs of model and version. E.g. "T2B1=2.6.1"')
@click.option("-n", "--dry-run", is_flag=True, help="Do not write changes")
@click.option("-f", "--force", is_flag=True, help="Proceed even with bad version/device info")
@click.option("--skip-testnets/--no-skip-testnets", default=True, help="Automatically exclude testnets")
# fmt: on
@click.pass_context
def release(
    ctx,
    releases: list[str],
    dry_run: bool,
    force: bool,
    skip_testnets: bool,
):
    """Release a new Trezor firmware.

    Update support infos so that all coins have a clear support status.
    By default, marks duplicate tokens and testnets as unsupported, and all coins that
    don't have support info are set to the released firmware version.

    The tool will ask you to confirm each added coin.
    """
    # Transforming the user release input into a dict and validating
    user_releases_dict = {
        key: val for key, val in (release.split("=") for release in releases)
    }
    for key in user_releases_dict:
        if key not in MODELS:
            raise click.ClickException(f"Unknown device: {key} - allowed are: {MODELS}")

    def bump_version(version_tuple: tuple[int]) -> str:
        version_list = list(version_tuple)
        version_list[-1] += 1
        return ".".join(str(n) for n in version_list)

    latest_releases = coin_info.latest_releases()

    # Take version either from user or guess it from latest releases info
    device_release_version: dict[str, str] = {}
    for device in MODELS:
        if device in user_releases_dict:
            device_release_version[device] = user_releases_dict[device]
        else:
            device_release_version[device] = bump_version(latest_releases[device])

    for device, version in device_release_version.items():
        version_starting_num = device[1]  # "T1B1" -> "1", "T2B1" -> "2"
        if not force and not version.startswith(version_starting_num + "."):
            raise click.ClickException(
                f"Device {device} should not be version {version}. "
                "Use --force to proceed anyway."
            )

        print(f"Releasing {device} firmware version {version}")

    defs, _ = coin_info.coin_info_with_duplicates()
    coins_dict = defs.as_dict()

    # Invoke data fixup as dry-run. That will modify data internally but won't write
    # changes. We will write changes at the end based on our own `dry_run` value.
    print("Fixing up data...")
    ctx.invoke(fix, dry_run=True)

    def maybe_add(coin):
        add = click.confirm(
            f"Add missing coin {coin['key']} ({coin['name']})?", default=True
        )
        if not add:
            unsupport_reason = click.prompt(
                "Enter reason for not supporting (blank to skip)",
                default="",
                show_default=False,
            )
            if not unsupport_reason:
                return

        for device, version in device_release_version.items():
            if add:
                support_setdefault(device, coin["key"], version)
            else:
                support_setdefault(device, coin["key"], False, unsupport_reason)

    # process missing (not listed) supportinfos
    missing_list = []
    unsupported = find_unsupported_coins(coins_dict)
    for val in unsupported.values():
        for coin in val:
            if coin not in missing_list:
                missing_list.append(coin)

    for coin in missing_list:
        if skip_testnets and coin["is_testnet"]:
            for device, version in device_release_version.items():
                support_setdefault(device, coin["key"], False, "(AUTO) exclude testnet")
        else:
            maybe_add(coin)

    if not dry_run:
        write_support_info()
    else:
        print("No changes written")


@cli.command()
@click.argument("keyword", nargs=-1, required=True)
def show(keyword):
    """Show support status of specified coins.

    Keywords match against key, name or shortcut (ticker symbol) of coin.
    """
    defs, _ = coin_info.coin_info_with_duplicates()

    for kw in keyword:
        for coin in coin_info.search(defs, kw):
            print_support(coin)


@cli.command(name="set")
# fmt: off
@click.argument("key", required=True)
@click.argument("entries", nargs=-1, required=True, metavar="entry=value [entry=value]...")
@click.option("-r", "--reason", help="Reason for not supporting")
# fmt: on
def set_support_value(key, entries, reason):
    """Set a support info variable.

    Examples:
    support.py set coin:BTC T1B1=1.10.5 T2T1=2.4.7 T2B1=no

    Setting a variable to a particular version string (e.g., "2.4.7") will set that
    particular version as the earliest supported.

    Setting a variable to "yes", "true" or "1" sets support to the upcoming release,
    as fetched via `coin_info.latest_releases()`.

    Setting a variable to "no", "false" or "0" sets support to false. You will need to
    provide a reason for unsupporting, either via the `-r` option, or interactively.

    Setting variable to empty ("T1B1=") will set to null, or clear the entry.
    """
    defs, _ = coin_info.coin_info_with_duplicates()
    coins = defs.as_dict()
    if key not in coins:
        click.echo(f"Failed to find key {key}")
        click.echo("Use 'support.py show' to search for the right one.")
        sys.exit(1)

    latest_releases = coin_info.latest_releases()
    next_releases = {
        k: (maj, min, pat + 1) for k, (maj, min, pat) in latest_releases.items()
    }

    for entry in entries:
        try:
            device, value = entry.split("=", maxsplit=1)
        except ValueError:
            click.echo(f"Invalid entry: {entry}")
            sys.exit(2)

        if device not in SUPPORT_INFO:
            raise click.ClickException(f"unknown device: {device}")

        if value in ("yes", "true", "1"):
            set_supported(device, key, next_releases[device])
        elif value in ("no", "false", "0"):
            if not reason:
                reason = click.prompt(f"Enter reason for not supporting on {device}:")
            set_unsupported(device, key, reason)
        elif value == "":
            clear_support(device, key)
        else:
            # arbitrary string
            set_supported(device, key, value)

    print_support(coins[key])
    write_support_info()


if __name__ == "__main__":
    cli()
