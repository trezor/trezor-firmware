#!/usr/bin/env python3
"""Updates maxfee_kb in given JSON coin definitions."""
import glob
import json
import logging
import math
import os.path
import re
import sys

import click

import coin_info
import marketcap

DEFAULT_SKIP_RE = (
    r"^Bitcoin$",
    r"^Regtest$",
    r"Testnet",
)
MAX_DELTA_PERCENT = 25


def round_sats(sats, precision=1):
    """
    Truncates `sats` down to a number with more trailing zeros.

    The result is comprised of `precision`+1 of leading digits followed by rest of zeros.

    >>> round_sats(123456789, precision=2)
    123000000
    >>> round_sats(123456789, precision=0)
    100000000
    """
    exp = math.floor(math.log10(sats))
    div = 10 ** (exp - precision)
    return sats // div * div


def compute_maxfee(maxcost, price, txsize):
    coins_per_tx = maxcost / price
    sats_per_tx = coins_per_tx * 10**8
    tx_per_kb = 1024.0 / txsize
    sats_per_kb = sats_per_tx * tx_per_kb
    return int(sats_per_kb)


def delta_percent(old, new):
    return int(abs(new - old) / old * 100.0)


def setup_logging(verbose):
    log_level = logging.DEBUG if verbose else logging.WARNING
    root = logging.getLogger()
    root.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    root.addHandler(handler)


@click.command()
# fmt: off
@click.argument("filename", nargs=-1, type=click.Path(writable=True))
@click.option("-m", "--cost", type=float, default=10.0, show_default=True, help="Maximum transaction fee in USD")
@click.option("-s", "--txsize", type=int, default=250, show_default=True, help="Transaction size in bytes")
@click.option("-S", "--skip", type=str, multiple=True, help="Regex of coin name to skip, can be used multiple times")
@click.option("-r", "--refresh", "refresh", flag_value=True, default=None, help="Force refresh market cap info")
@click.option("-R", "--no-refresh", "refresh", flag_value=False, default=None, help="Force use cached market cap info")
@click.option("-A", "--api-key", required=True, envvar="COINMARKETCAP_API_KEY", help="Coinmarketcap API key")
@click.option("-v", "--verbose", is_flag=True, help="Display more info")
# fmt: on
def main(filename, cost, skip, txsize, refresh, api_key, verbose):
    """
    Updates maxfee_kb in JSON coin definitions.

    The new value is calculated from the --cost argument which specifies maximum
    transaction fee in fiat denomination. The fee is converted to coin value
    using current price data. Then per-kilobyte fee is computed using given
    transaction size.

    If no filenames are provided, all definitions except Bitcoin and testnets
    are updated.
    """
    setup_logging(verbose)
    marketcap.init(api_key, refresh=refresh)

    if len(filename) > 0:
        coin_files = filename
    else:
        coin_files = glob.glob(os.path.join(coin_info.DEFS_DIR, "bitcoin", "*.json"))
        if len(skip) == 0:
            skip = DEFAULT_SKIP_RE

    for filename in sorted(coin_files):
        coin = coin_info.load_json(filename)
        short = coin["coin_shortcut"]

        if any(re.search(s, coin["coin_name"]) is not None for s in skip):
            logging.warning(f"{short}:\tskipping because --skip matches")
            continue

        price = marketcap.fiat_price(short)
        if price is None:
            logging.error(f"{short}:\tno price data, skipping")
            continue

        old_maxfee_kb = coin["maxfee_kb"]
        new_maxfee_kb = round_sats(compute_maxfee(cost, price, txsize))
        if old_maxfee_kb != new_maxfee_kb:
            coin["maxfee_kb"] = new_maxfee_kb
            with open(filename, "w") as fh:
                json.dump(coin, fh, indent=2)
                fh.write("\n")
            logging.info(f"{short}:\tupdated {old_maxfee_kb} -> {new_maxfee_kb}")
            delta = delta_percent(old_maxfee_kb, new_maxfee_kb)
            if delta > MAX_DELTA_PERCENT:
                logging.warning(f"{short}:\tprice has changed by {delta} %")
        else:
            logging.info(f"{short}:\tno change")


if __name__ == "__main__":
    main()
