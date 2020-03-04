#!/usr/bin/env python3
# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import json
import sys
from decimal import Decimal
from pathlib import Path

import click
import requests

from trezorlib import btc, messages, protobuf

REPOSITORY_ROOT = Path(__file__).parent.parent
TOOLS_PATH = REPOSITORY_ROOT / "common" / "tools"
CACHE_PATH = Path(__file__).parent / "txcache"

sys.path.insert(0, str(TOOLS_PATH))
from coin_info import coin_info  # isort:skip


def _get_blockbooks():
    """Make a list of blockbook URL patterns available.

    Only used to prefill the BLOCKBOOKS variable.
    """
    coins = coin_info().bitcoin
    res = {}
    for coin in coins:
        if not coin.get("blockbook"):
            continue

        res[coin["coin_name"].lower()] = coin["blockbook"][0] + "/api/tx-specific/{}"
    return res


BLOCKBOOKS = _get_blockbooks()


class TxCache:
    def __init__(self, coin_name):
        self.slug = coin_name.lower().replace(" ", "_")

    def get_tx(self, txhash):
        try:
            (CACHE_PATH / self.slug).mkdir()
        except Exception:
            pass

        cache_file = CACHE_PATH / self.slug / f"{txhash}.json"
        if not cache_file.exists():
            raise RuntimeError(
                f"cache miss for {self.slug} tx {txhash}.\n"
                "To fix, refer to ./tests/tx_cache.py --help"
            )

        txdict = json.loads(cache_file.read_text())
        return protobuf.dict_to_proto(messages.TransactionType, txdict)

    def __getitem__(self, key):
        return self.get_tx(key.hex())


@click.command()
@click.argument("coin_name")
@click.argument("tx", metavar="TXHASH_OR_URL")
def cli(tx, coin_name):
    """Add a transaction to the cache.

    \b
    Without URL, default blockbook server will be used:
    ./tests/tx_cache.py bcash bc37c28dfb467d2ecb50261387bf752a3977d7e5337915071bb4151e6b711a78
    It is also possible to specify URL explicitly:
    ./tests/tx_cache.py bcash https://bch1.trezor.io/api/tx-specific/bc37c28dfb467d2ecb50261387bf752a3977d7e5337915071bb4151e6b711a78

    The transaction will be parsed into Trezor format and saved in
    tests/txcache/<COIN_NAME>/<TXHASH>.json. Note that only Bitcoin-compatible fields
    will be filled out. If you are adding a coin with special fields (Dash, Zcash...),
    it is your responsibility to fill out the missing fields properly.
    """
    if tx.startswith("http"):
        tx_url = tx
        tx_hash = tx.split("/")[-1].lower()

    elif coin_name not in BLOCKBOOKS:
        raise click.ClickException(
            f"Could not find blockbook for {coin_name}. Please specify a full URL."
        )

    else:
        tx_hash = tx.lower()
        tx_url = BLOCKBOOKS[coin_name].format(tx)

    click.echo(f"Fetching from {tx_url}...")
    try:
        tx_src = requests.get(tx_url).json(parse_float=Decimal)
        tx_proto = btc.from_json(tx_src)
        tx_dict = protobuf.to_dict(tx_proto)
        tx_json = json.dumps(tx_dict, sort_keys=True, indent=2) + "\n"
    except Exception as e:
        raise click.ClickException(e) from e

    cache_dir = CACHE_PATH / coin_name
    if not cache_dir.exists():
        cache_dir.mkdir()
    (cache_dir / f"{tx_hash}.json").write_text(tx_json)
    click.echo(tx_json)


if __name__ == "__main__":
    cli()
