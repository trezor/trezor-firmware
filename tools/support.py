#!/usr/bin/env python3
import os
import sys
import click
import coin_info
import json

SUPPORT_INFO = coin_info.get_support_data()

MANDATORY_ENTRIES = ("trezor1", "trezor2", "connect", "webwallet")


def update_support(key, entry, value):
    # template entry
    support = {k: None for k in MANDATORY_ENTRIES}
    support["other"] = {}
    # fill out actual support info, if it exists
    support.update(SUPPORT_INFO.get(key, {}))

    if entry in MANDATORY_ENTRIES:
        if entry.startswith("trezor") and not value:
            value = None
        support[entry] = value
    else:
        support["other"][entry] = value

    for k in support["other"]:
        if not support["other"][k]:
            del support["other"][k]

    if not support["other"]:
        del support["other"]

    SUPPORT_INFO[key] = support
    return support


def write_support_info():
    with open(os.path.join(coin_info.DEFS_DIR, "support.json"), "w") as f:
        json.dump(SUPPORT_INFO, f, indent=4)
        f.write("\n")


@click.group()
def cli():
    pass


@cli.command()
def rewrite():
    """Regenerate support.json to match predefined structure and field order."""
    for key, coin in SUPPORT_INFO.items():
        d = {"trezor1": None, "trezor2": None, "connect": None, "webwallet": None}
        d.update(coin)
        if "electrum" in d:
            del d["electrum"]
        if "other" in d and not d["other"]:
            del d["other"]
        SUPPORT_INFO[key] = d

    write_support_info()


@cli.command()
def check():
    """Check validity of support information.

    The relevant code is actually part of 'coin_gen.py'. It can be invoked from
    here for convenience and because it makes sense. But it's preferable to run it
    as part of 'coin_gen.py check'.
    """
    defs = coin_info.get_all()
    support_data = coin_info.get_support_data()
    import coin_gen

    if not coin_gen.check_support(defs, support_data, fail_missing=True):
        sys.exit(1)


@cli.command()
@click.argument("keyword", nargs=-1)
def show(keyword):
    """Show support status of specified coins.

    Keywords match against key, name or shortcut (ticker symbol) of coin. If no
    keywords are provided, show all supported coins.

    Only coins listed in support.json are considered "supported". That means that
    Ethereum networks, ERC20 tokens and NEM mosaics will probably show up wrong.
    """
    defs = coin_info.get_all().as_list()

    if keyword:
        for coin in defs:
            key = coin["key"]
            name, shortcut = coin["name"], coin["shortcut"]
            for kw in keyword:
                kwl = kw.lower()
                if kwl == key.lower() or kwl in name.lower() or kwl == shortcut.lower():
                    print("{} - {} ({})".format(key, name, shortcut), end=" - ")
                    if key in SUPPORT_INFO:
                        print(json.dumps(SUPPORT_INFO[key], indent=4))
                    else:
                        print("no support info")
                    break

    else:
        print(json.dumps(SUPPORT_INFO, indent=4))


@cli.command()
@click.argument("support_key", required=True)
@click.argument(
    "entries", nargs=-1, required=True, metavar="entry=value [entry=value]..."
)
@click.option(
    "-n",
    "--dry-run",
    is_flag=True,
    help="Only print updated support info, do not write back",
)
def set(support_key, entries, dry_run):
    """Set a support info variable.

    Examples:
    support.py coin:BTC trezor1=soon trezor2=2.0.7 webwallet=yes connect=no
    support.py coin:LTC trezor1=yes "Electrum-LTC=https://electrum-ltc.org" Electrum=

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
    coins = coin_info.get_all().as_dict()
    if support_key not in coins:
        click.echo("Failed to find key {}".format(support_key))
        click.echo("Use 'support.py show' to search for the right one.")
        sys.exit(1)

    print("{} - {}".format(support_key, coins[support_key]["name"]))

    for entry in entries:
        try:
            key, value = entry.split("=", maxsplit=1)
        except ValueError:
            click.echo("Invalid entry: {}".format(entry))
            sys.exit(2)

        if value in ("yes", "true", "1"):
            value = True
        elif value in ("no", "false", "2"):
            value = False
        elif value == "":
            value = None

        support = update_support(support_key, key, value)

    print(json.dumps(support, indent=4))
    if not dry_run:
        write_support_info()


if __name__ == "__main__":
    cli()
