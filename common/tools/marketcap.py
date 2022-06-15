#!/usr/bin/env python3
"""Fetch market capitalization data."""
import json
import os
import time

import requests

COINMAKETCAP_CACHE = os.path.join(os.path.dirname(__file__), "coinmarketcap.json")
COINMARKETCAP_API_BASE = "https://pro-api.coinmarketcap.com/v1/"

COINS_SEARCHABLE = {}


def call(endpoint, api_key, params=None):
    url = COINMARKETCAP_API_BASE + endpoint
    r = requests.get(url, params=params, headers={"X-CMC_PRO_API_KEY": api_key})
    r.raise_for_status()
    return r.json()


def init(api_key, refresh=None):
    global COINS_SEARCHABLE

    force_refresh = refresh is True
    disable_refresh = refresh is False
    try:
        try:
            mtime = os.path.getmtime(COINMAKETCAP_CACHE)
        except FileNotFoundError:
            mtime = 0
        cache_is_fresh = mtime > time.time() - 3600
        if disable_refresh or (cache_is_fresh and not force_refresh):
            print("Using cached market cap data")
            with open(COINMAKETCAP_CACHE) as f:
                coinmarketcap_data = json.load(f)
        else:
            print("Fetching market cap data")
            coinmarketcap_data = call(
                "cryptocurrency/listings/latest",
                api_key,
                params={"limit": 5000, "convert": "USD"},
            )
            by_id = {str(coin["id"]): coin for coin in coinmarketcap_data["data"]}
            all_ids = list(by_id.keys())
            while all_ids:
                first_100 = all_ids[:100]
                all_ids = all_ids[100:]
                time.sleep(2.2)
                print(f"Fetching metadata, {len(all_ids)} coins remaining...")
                metadata = call(
                    "cryptocurrency/info", api_key, params={"id": ",".join(first_100)}
                )
                for coin_id, meta in metadata["data"].items():
                    by_id[coin_id]["meta"] = meta

            with open(COINMAKETCAP_CACHE, "w") as f:
                json.dump(coinmarketcap_data, f)
    except Exception as e:
        raise RuntimeError("market cap data unavailable") from e

    data_searchable = {}
    for coin in coinmarketcap_data["data"]:
        slug = coin["slug"]
        symbol = coin["symbol"]
        platform = coin["meta"]["platform"]
        data_searchable[slug] = data_searchable[symbol] = coin
        if platform is not None and platform["name"] == "Ethereum":
            address = platform["token_address"].lower()
            data_searchable[address] = coin
        for explorer in coin["meta"]["urls"]["explorer"]:
            # some tokens exist in multiple places, such as BNB and ETH
            # then the "platform" field might list the wrong thing
            # to be sure, walk the list of explorers and look for etherscan.io
            if explorer.startswith("https://etherscan.io/token/"):
                address = explorer.rsplit("/", 1)[-1].lower()
                data_searchable[address] = coin

    COINS_SEARCHABLE = data_searchable


def fiat_price(coin_symbol):
    data = COINS_SEARCHABLE.get(coin_symbol)
    if data is None:
        return None

    return data["quote"]["USD"]["price"]
