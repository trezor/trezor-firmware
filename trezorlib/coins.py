import os.path
import json

from .tx_api import TxApiInsight, TxApiBlockCypher

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
        coins_list = json.load(coins_json)
        return {coin['coin_name']: coin for coin in coins_list}


def _insight_for_coin(coin):
    if not coin['bitcore']:
        return None
    zcash = coin['coin_name'].lower().startswith('zcash')
    network = 'insight_{}'.format(coin['coin_name'].lower().replace(' ', '_'))
    url = coin['bitcore'][0] + '/api/'
    return TxApiInsight(network=network, url=url, zcash=zcash)


# exported variables
__all__ = ['by_name', 'slip44', 'tx_api']

try:
    by_name = _load_coins_json()
except Exception as e:
    raise ImportError("Failed to load coins.json. Check your installation.") from e

slip44 = {name: coin['bip44'] for name, coin in by_name.items()}
tx_api = {name: _insight_for_coin(coin)
          for name, coin in by_name.items()
          if coin["bitcore"]}

# fixup for Dogecoin
tx_api['Dogecoin'] = TxApiBlockCypher(network='blockcypher_dogecoin', url='https://api.blockcypher.com/v1/doge/main/')
