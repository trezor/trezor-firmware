import decimal
import json
import os.path

from trezorlib import coins
from trezorlib.tx_api import json_to_tx

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "txcache")


def tx_cache(coin_name, allow_fetch=True):
    coin_data = coins.by_name[coin_name]
    fetch = coins.tx_api[coin_name].get_tx_data if allow_fetch else None
    return TxCache(CACHE_PATH, coin_data, fetch)


class TxCache:
    def __init__(self, path, coin_data, fetch=None):
        self.path = path
        self.coin_data = coin_data
        self.fetch = fetch

        coin_slug = coin_data["coin_name"].lower().replace(" ", "_")
        prefix = "insight_" + coin_slug + "_tx_"
        self.file_pattern = os.path.join(self.path, prefix + "{}.json")

    def get_tx(self, txhash):
        cache_file = self.file_pattern.format(txhash)

        try:
            with open(cache_file) as f:
                data = json.load(f, parse_float=decimal.Decimal)
                return json_to_tx(self.coin_data, data)
        except Exception as e:
            if self.fetch is None:
                raise Exception("Unhandled cache miss") from e

        # cache miss, try to use backend
        data = self.fetch(txhash)
        with open(cache_file, "w") as f:
            json.dump(data, f)
        return json_to_tx(self.coin_data, data)

    def __getitem__(self, key):
        return self.get_tx(key.hex())
