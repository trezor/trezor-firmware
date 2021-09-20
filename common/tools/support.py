#!/usr/bin/env python3
import json
import os
import re
import sys

import click

import coin_info

SUPPORT_INFO = coin_info.get_support_data()

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
    def support_value(where, key, missing_means_no=False):
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
        elif missing_means_no:
            return "NO"
        else:
            return "support info missing"

    key, name, shortcut = coin["key"], coin["name"], coin["shortcut"]
    print(f"{key} - {name} ({shortcut})")
    if coin.get("duplicate"):
        print(" * DUPLICATE SYMBOL")
    for dev, where in SUPPORT_INFO.items():
        missing_means_no = dev in coin_info.MISSING_SUPPORT_MEANS_NO
        print(" *", dev, ":", support_value(where, key, missing_means_no))


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
        if not isinstance(supported, dict):
            errors.append(f"Missing 'supported' dict for {device}")
        else:
            for key, value in supported.items():
                try:
                    if device in coin_info.VERSIONED_SUPPORT_INFO:
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
    for device in coin_info.VERSIONED_SUPPORT_INFO:
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


def find_supported_duplicate_tokens(coins_dict):
    result = []
    for _, supported, _ in all_support_dicts():
        for key in supported:
            if not key.startswith("erc20:"):
                continue
            if coins_dict.get(key, {}).get("duplicate"):
                result.append(key)
    return result


def process_erc20(coins_dict):
    """Make sure that:
    * orphaned ERC20 support info is cleared out
    * duplicate ERC20 tokens are not listed as supported
    * non-duplicate ERC20 tokens are cleared out from the unsupported list
    """
    erc20_dict = {
        key: coin.get("duplicate", False)
        for key, coin in coins_dict.items()
        if coin_info.is_token(coin)
    }
    for device, supported, unsupported in all_support_dicts():
        nondups = set()
        dups = set(key for key, value in erc20_dict.items() if value)
        for key in supported:
            if key not in erc20_dict:
                continue
            if not erc20_dict[key]:
                dups.discard(key)

        for key in unsupported:
            if key not in erc20_dict:
                continue
            # ignore dups that are unsupported now
            dups.discard(key)

            if not erc20_dict[key] and unsupported[key] == ERC20_DUPLICATE_KEY:
                # remove duplicate status
                nondups.add(key)

        for key in dups:
            if device in coin_info.MISSING_SUPPORT_MEANS_NO:
                clear_support(device, key)
            else:
                print(f"ERC20 on {device}: adding duplicate {key}")
                set_unsupported(device, key, ERC20_DUPLICATE_KEY)

        for key in nondups:
            print(f"ERC20 on {device}: clearing non-duplicate {key}")
            clear_support(device, key)


def clear_erc20_mixed_buckets(buckets):
    for bucket in buckets.values():
        tokens = [coin for coin in bucket if coin_info.is_token(coin)]
        if tokens == bucket:
            continue

        if len(tokens) == 1:
            tokens[0]["duplicate"] = False


@click.group()
def cli():
    pass


@cli.command()
@click.option("-n", "--dry-run", is_flag=True, help="Do not write changes")
def fix(dry_run):
    """Fix expected problems.

    Prunes orphaned keys and ensures that ERC20 duplicate info matches support info.
    """
    all_coins, buckets = coin_info.coin_info_with_duplicates()
    clear_erc20_mixed_buckets(buckets)
    coins_dict = all_coins.as_dict()

    orphaned = find_orphaned_support_keys(coins_dict)
    for orphan in orphaned:
        print(f"pruning orphan {orphan}")
        for device in SUPPORT_INFO:
            clear_support(device, orphan)

    process_erc20(coins_dict)
    if not dry_run:
        write_support_info()


@cli.command()
# fmt: off
@click.option("-T", "--check-tokens", is_flag=True, help="Also check unsupported ERC20 tokens, ignored by default")
@click.option("-m", "--ignore-missing", is_flag=True, help="Do not fail on missing supportinfo")
# fmt: on
def check(check_tokens, ignore_missing):
    """Check validity of support information.

    Ensures that `support.json` data is well formed, there are no keys without
    corresponding coins, and there are no coins without corresponding keys.

    If `--check-tokens` is specified, the check will also take into account ERC20 tokens
    without support info. This is disabled by default, because support info for ERC20
    tokens is not strictly required.

    If `--ignore-missing` is specified, the check will display coins with missing
    support info, but will not fail when missing coins are found. This is
    useful in Travis.
    """
    all_coins, buckets = coin_info.coin_info_with_duplicates()
    clear_erc20_mixed_buckets(buckets)
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
        if not check_tokens:
            values = [coin for coin in values if not coin_info.is_token(coin)]
        if values:
            if not ignore_missing:
                checks_ok = False
            print(f"Device {device} has missing support infos:")
            for coin in values:
                print(f"{coin['key']} - {coin['name']}")

    supported_dups = find_supported_duplicate_tokens(coins_dict)
    for key in supported_dups:
        coin = coins_dict[key]
        checks_ok = False
        print(f"Token {coin['key']} ({coin['name']}) is duplicate but supported")

    if not checks_ok:
        print("Some checks have failed")
        sys.exit(1)


@cli.command()
# fmt: off
@click.option("--v1", help="Version for T1 release (default: guess from latest)")
@click.option("--v2", help="Version for TT release (default: guess from latest)")
@click.option("-n", "--dry-run", is_flag=True, help="Do not write changes")
@click.option("-f", "--force", is_flag=True, help="Proceed even with bad version/device info")
@click.option("-v", "--verbose", is_flag=True, help="Be more verbose")
@click.option("--skip-testnets/--no-skip-testnets", default=True, help="Automatically exclude testnets")
# fmt: on
@click.pass_context
def release(
    ctx,
    v1,
    v2,
    dry_run,
    force,
    verbose,
    skip_testnets,
):
    """Release a new Trezor firmware.

    Update support infos so that all coins have a clear support status.
    By default, marks duplicate tokens and testnets as unsupported, and all coins that
    don't have support info are set to the released firmware version.

    The tool will ask you to confirm each added coin. ERC20 tokens are added
    automatically. Use `--verbose` to see them.
    """
    latest_releases = coin_info.latest_releases()

    def bump_version(version_tuple):
        version_list = list(version_tuple)
        version_list[-1] += 1
        return ".".join(str(n) for n in version_list)

    # guess `version` if not given
    if not v1:
        v1 = bump_version(latest_releases["trezor1"])
    if not v2:
        v2 = bump_version(latest_releases["trezor2"])

    versions = {"trezor1": v1, "trezor2": v2}

    for number in "1", "2":
        device = f"trezor{number}"
        version = versions[device]
        if not force and not version.startswith(number + "."):
            raise click.ClickException(
                f"Device trezor{device} should not be version {version}. "
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

        for device, version in versions.items():
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

    tokens = [coin for coin in missing_list if coin_info.is_token(coin)]
    nontokens = [coin for coin in missing_list if not coin_info.is_token(coin)]
    for coin in tokens:
        key = coin["key"]
        # assert not coin.get("duplicate"), key
        if verbose:
            print(f"Adding missing {key} ({coin['name']})")
        for device, version in versions.items():
            support_setdefault(device, key, version)

    for coin in nontokens:
        if skip_testnets and "testnet" in coin["name"].lower():
            for device, version in versions.items():
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
    support.py set coin:BTC trezor1=1.10.5 trezor2=2.4.7 suite=yes connect=no
    support.py set coin:LTC trezor1=yes connect=

    Setting a variable to "yes", "true" or "1" sets support to true.
    Setting a variable to "no", "false" or "0" sets support to false.
    (or null, in case of trezor1/2)
    Setting variable to empty ("trezor1=") will set to null, or clear the entry.
    Setting a variable to a particular version string (e.g., "2.4.7") will set that
    particular version.
    """
    defs, _ = coin_info.coin_info_with_duplicates()
    coins = defs.as_dict()
    if key not in coins:
        click.echo(f"Failed to find key {key}")
        click.echo("Use 'support.py show' to search for the right one.")
        sys.exit(1)

    if coins[key].get("duplicate") and coin_info.is_token(coins[key]):
        shortcut = coins[key]["shortcut"]
        click.echo(f"Note: shortcut {shortcut} is a duplicate.")

    for entry in entries:
        try:
            device, value = entry.split("=", maxsplit=1)
        except ValueError:
            click.echo(f"Invalid entry: {entry}")
            sys.exit(2)

        if device not in SUPPORT_INFO:
            raise click.ClickException(f"unknown device: {device}")

        if value in ("yes", "true", "1"):
            set_supported(device, key, True)
        elif value in ("no", "false", "0"):
            if device in coin_info.MISSING_SUPPORT_MEANS_NO:
                click.echo(f"Setting explicitly unsupported for {device}.")
                click.echo(f"Perhaps you meant removing support, i.e., '{device}=' ?")
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
