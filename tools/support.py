#!/usr/bin/env python3
import re
import os
import sys
import click
import coin_info
import json

SUPPORT_INFO = coin_info.get_support_data()
MISSING_MEANS_NO = ("connect", "webwallet")
VERSIONED_SUPPORT_INFO = ("trezor1", "trezor2")

VERSION_RE = re.compile(r"\d+.\d+.\d+")


def write_support_info():
    with open(os.path.join(coin_info.DEFS_DIR, "support.json"), "w") as f:
        json.dump(SUPPORT_INFO, f, indent=2, sort_keys=True)
        f.write("\n")


def print_support(coin):
    def support_value(where, key, missing_means_no=False):
        if "supported" in where and key in where["supported"]:
            val = where["supported"][key]
            if val is True:
                return "YES"
            elif val == "soon":
                return "SOON"
            elif VERSION_RE.match(val):
                return f"YES since {val}"
            else:
                return f"BAD VALUE {val}"
        elif "unsupported" in where and key in where["unsupported"]:
            val = where["unsupported"][key]
            return f"NO (reason: {val})"
        elif missing_means_no:
            return "NO"
        else:
            return "support info missing"

    key, name, shortcut = coin["key"], coin["name"], coin["shortcut"]
    print(f"{key} - {name} ({shortcut})")
    if coin.get("duplicate"):
        print(" * DUPLICATE SYMBOL (no support)")
    else:
        for dev, where in SUPPORT_INFO.items():
            missing_means_no = dev in MISSING_MEANS_NO
            print(" *", dev, ":", support_value(where, key, missing_means_no))


# ====== validation functions ====== #


def check_support_values():
    def _check_value_version_soon(val):
        if not isinstance(value, str):
            raise ValueError(f"non-str value: {value}")

        is_version = VERSION_RE.match(value)
        is_soon = value == "soon"
        if not (is_version or is_soon):
            raise ValueError(f"expected version or 'soon', found '{value}'")

    errors = []
    for device, values in SUPPORT_INFO.items():
        supported = values.get("supported")
        if not isinstance(supported, dict):
            errors.append(f"Missing 'supported' dict for {device}")
        else:
            for key, value in supported.items():
                try:
                    if device in VERSIONED_SUPPORT_INFO:
                        _check_value_version_soon(value)
                    else:
                        if value is not True:
                            raise ValueError(f"only allowed is True, but found {value}")
                except Exception as e:
                    errors.append(f"{device}.supported.{key}: {e}")

        unsupported = values.get("unsupported")
        if not isinstance(unsupported, dict):
            errors.append(f"Missing 'supported' dict for {device}")
        else:
            for key, value in unsupported.items():
                if not isinstance(value, str) or not value:
                    errors.append(f"{device}.unsupported.{key}: missing reason")

    return errors


def find_unsupported_coins(coins_dict):
    result = {}
    for device in VERSIONED_SUPPORT_INFO:
        values = SUPPORT_INFO[device]
        support_set = set()
        support_set.update(values["supported"].keys())
        support_set.update(values["unsupported"].keys())

        result[device] = unsupported = []
        for key, coin in coins_dict.items():
            if coin.get("duplicate"):
                continue
            if key not in support_set:
                unsupported.append(coin)

    return result


def find_orphaned_support_keys(coins_dict):
    result = {}
    for device, values in SUPPORT_INFO.items():
        device_res = {}
        for supkey, supvalues in values.items():
            orphans = set()
            for coin_key in supvalues.keys():
                if coin_key not in coins_dict:
                    orphans.add(coin_key)
            device_res[supkey] = orphans
        result[device] = device_res

    return result


@click.group()
def cli():
    pass


@cli.command()
# fmt: off
@click.option("-p", "--prune-orphans", is_flag=True, help="Remove orphaned keys for which there is no corresponding coin info")
@click.option("-t", "--ignore-tokens", is_flag=True, help="Ignore unsupported ERC20 tokens")
# fmt: on
def check(prune_orphans, ignore_tokens):
    """Check validity of support information.

    Ensures that `support.json` data is well formed, there are no keys without
    corresponding coins, and there are no coins without corresponding keys.

    If `--prune-orphans` is specified, orphaned keys (no corresponding coin)
    will be deleted from `support.json`.

    If `--ignore-tokens` is specified, the check will ignore ERC20 tokens
    without support info. This is useful because there is usually a lot of ERC20
    tokens.
    """
    coins_dict = coin_info.get_all(deduplicate=False).as_dict()
    checks_ok = True

    errors = check_support_values()
    if errors:
        for error in errors:
            print(error)
        checks_ok = False

    orphaned = find_orphaned_support_keys(coins_dict)
    for device, values in orphaned.items():
        for supkey, supvalues in values.items():
            for key in supvalues:
                print(f"orphaned key {device} -> {supkey} -> {key}")
                if prune_orphans:
                    del SUPPORT_INFO[device][supkey][key]
                else:
                    checks_ok = False

    if prune_orphans:
        write_support_info()

    missing = find_unsupported_coins(coins_dict)
    for device, values in missing.items():
        if ignore_tokens:
            values = [coin for coin in values if not coin["key"].startswith("erc20:")]
        if values:
            checks_ok = False
            print(f"Device {device} has missing support infos:")
            for coin in values:
                print(f"{coin['key']} - {coin['name']}")

    if not checks_ok:
        print("Some checks have failed")
        sys.exit(1)


@cli.command()
# fmt: off
@click.argument("version")
@click.option("--git-tag/--no-git-tag", "-g", default=False, help="create a corresponding Git tag")
@click.option("--soon/--no-soon", default=True, help="Release coins marked 'soon'")
@click.option("--missing/--no-missing", default=True, help="Release coins with missing support info")
@click.option("-n", "--dry-run", is_flag=True, help="Do not write changes")
# fmt: on
def release(version, git_tag, soon, missing, dry_run):
    """Release a new Trezor firmware.

    Update support infos so that all coins have a clear support status.
    By default, marks duplicate tokens as unsupported, and all coins that either
    don't have support info, or they are supported "soon", are set to the
    released firmware version.

    Optionally tags the repository with the given version.
    """
    version_tuple = list(map(int, version.split(".")))
    device = f"trezor{version_tuple[0]}"

    print(f"Releasing {device} firmware version {version}")

    defs = coin_info.get_all(deduplicate=False)
    coin_info.mark_duplicate_shortcuts(defs.as_list())
    coins_dict = defs.as_dict()

    if missing:
        missing_list = find_unsupported_coins(coins_dict)[device]
        for coin in missing_list:
            key = coin["key"]
            if coin.get("duplicate"):
                print(f"UNsupporting duplicate coin {key} ({coin['name']})")
                SUPPORT_INFO[device]["unsupported"][key] = "duplicate key"
            else:
                print(f"Adding missing {key} ({coin['name']})")
                SUPPORT_INFO[device]["supported"][key] = version

    if soon:
        soon_list = [
            coins_dict[key]
            for key, val in SUPPORT_INFO[device]["supported"].items()
            if val == "soon" and key in coins_dict
        ]
        for coin in soon_list:
            key = coin["key"]
            print(f"Adding soon-released {key} ({coin['name']})")
            SUPPORT_INFO[device]["supported"][key] = version

    if git_tag:
        print("git tag not supported yet")

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
    defs = coin_info.get_all(deduplicate=False).as_list()
    coin_info.mark_duplicate_shortcuts(defs)

    for coin in defs:
        key = coin["key"].lower()
        name = coin["name"].lower()
        shortcut = coin["shortcut"].lower()
        symsplit = shortcut.split(" ", maxsplit=1)
        symbol = symsplit[0]
        suffix = symsplit[1] if len(symsplit) > 1 else ""
        for kw in keyword:
            kwl = kw.lower()
            if (
                kwl == key
                or kwl in name
                or kwl == shortcut
                or kwl == symbol
                or kwl in suffix
            ):
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
    support.py set coin:BTC trezor1=soon trezor2=2.0.7 webwallet=yes connect=no
    support.py set coin:LTC trezor1=yes connect=

    Setting a variable to "yes", "true" or "1" sets support to true.
    Setting a variable to "no", "false" or "0" sets support to false.
    (or null, in case of trezor1/2)
    Setting variable to empty ("trezor1=") will set to null, or clear the entry.
    Setting to "soon", "planned", "2.1.1" etc. will set the literal string.

    Entries that are always present:
    trezor1 trezor2 webwallet connect

    Entries with other names will be inserted into "others". This is a good place
    to store links to 3rd party software, such as Electrum forks or claim tools.
    """
    coins = coin_info.get_all(deduplicate=False).as_dict()
    coin_info.mark_duplicate_shortcuts(coins.values())
    if key not in coins:
        click.echo(f"Failed to find key {key}")
        click.echo("Use 'support.py show' to search for the right one.")
        sys.exit(1)

    if coins[key].get("duplicate"):
        shortcut = coins[key]["shortcut"]
        click.echo(f"Note: shortcut {shortcut} is a duplicate.")
        click.echo(f"Coin will NOT be listed regardless of support.json status.")

    for entry in entries:
        try:
            device, value = entry.split("=", maxsplit=1)
        except ValueError:
            click.echo(f"Invalid entry: {entry}")
            sys.exit(2)

        if device not in SUPPORT_INFO:
            raise click.ClickException(f"unknown device: {device}")

        where = SUPPORT_INFO[device]
        # clear existing info
        where["supported"].pop(key, None)
        where["unsupported"].pop(key, None)

        if value in ("yes", "true", "1"):
            where["supported"][key] = True
        elif value in ("no", "false", "0"):
            if device in MISSING_MEANS_NO:
                click.echo("Setting explicitly unsupported for {device}.")
                click.echo("Perhaps you meant removing support, i.e., '{device}=' ?")
            if not reason:
                reason = click.prompt(f"Enter reason for not supporting on {device}:")
            where["unsupported"][key] = reason
        elif value == "":
            # do nothing, existing info is cleared
            pass
        else:
            # arbitrary string?
            where["supported"][key] = value

    print_support(coins[key])
    write_support_info()


if __name__ == "__main__":
    cli()
