# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import os.path
import json

from .tx_api import TxApiInsight

COINS_JSON = os.path.join(os.path.dirname(__file__), 'coins.json')


def _load_coins_json():
    # Load coins.json to local variables
    # NOTE: coins.json comes from 'vendor/trezor-common/coins.json',
    # which is a git submodule. If you're trying to run trezorlib directly
    # from the checkout (or tarball), initialize the submodule with:
    # $ git submodule update --init
    # and install coins.json with:
    # $ python setup.py prebuild
    with open(COINS_JSON) as coins_json:
        return json.load(coins_json)


def _insight_for_coin(coin):
    url = next(iter(coin['blockbook'] + coin['bitcore']), None)
    if not url:
        return None
    zcash = coin['coin_name'].lower().startswith('zcash')
    bip115 = coin['bip115']
    network = 'insight_{}'.format(coin['coin_name'].lower().replace(' ', '_'))
    return TxApiInsight(network=network, url=url, zcash=zcash, bip115=bip115)


# exported variables
__all__ = ['by_name', 'slip44', 'tx_api']

try:
    by_name = _load_coins_json()
except Exception as e:
    raise ImportError("Failed to load coins.json. Check your installation.") from e

slip44 = {name: coin['slip44'] for name, coin in by_name.items()}
tx_api = {name: _insight_for_coin(coin)
          for name, coin in by_name.items()
          if coin["blockbook"] or coin["bitcore"]}
