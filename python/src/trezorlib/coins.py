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
import os.path

from .tx_api import TxApi

COINS_JSON = os.path.join(os.path.dirname(__file__), "coins.json")


def _load_coins_json():
    # Load coins.json to local variables
    # NOTE: coins.json is generated via `make coins_json` command.
    with open(COINS_JSON) as coins_json:
        return json.load(coins_json)


# exported variables
__all__ = ["by_name", "slip44", "tx_api"]

try:
    coins_list = _load_coins_json()
    by_name = {coin["coin_name"]: coin for coin in coins_list}
except Exception as e:
    raise ImportError("Failed to load coins.json. Check your installation.") from e

slip44 = {name: coin["slip44"] for name, coin in by_name.items()}
tx_api = {
    name: TxApi(coin)
    for name, coin in by_name.items()
    if coin["blockbook"] or coin["bitcore"]
}
