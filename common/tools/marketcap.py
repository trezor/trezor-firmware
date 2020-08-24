#!/usr/bin/env python3
"""Fetch market capitalization data."""
import json
import os
import time

import requests

COINMAKETCAP_CACHE = os.path.join(os.path.dirname(__file__), "coinmarketcap.json")
COINMARKETCAP_API_BASE = "https://pro-api.coinmarketcap.com/v1/"

MARKET_CAPS = {}
PRICES = {}


def call(endpoint, api_key, params=None):
    url = COINMARKETCAP_API_BASE + endpoint
    r = requests.get(url, params=params, headers={"X-CMC_PRO_API_KEY": api_key})
    r.raise_for_status()
    return r.json()


def init(api_key, refresh=None):
    global MARKET_CAPS, PRICES

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
                time.sleep(1)
                print("Fetching metadata, {} coins remaining...".format(len(all_ids)))
                metadata = call(
                    "cryptocurrency/info", api_key, params={"id": ",".join(first_100)}
                )
                for coin_id, meta in metadata["data"].items():
                    by_id[coin_id]["meta"] = meta

            with open(COINMAKETCAP_CACHE, "w") as f:
                json.dump(coinmarketcap_data, f)
    except Exception as e:
        raise RuntimeError("market cap data unavailable") from e

    cap_data = {}
    price_data = {}
    for coin in coinmarketcap_data["data"]:
        slug = coin["slug"]
        symbol = coin["symbol"]
        platform = coin["meta"]["platform"]
        market_cap = coin["quote"]["USD"]["market_cap"]
        price = coin["quote"]["USD"]["price"]
        if market_cap is not None:
            cap_data[slug] = int(market_cap)
            price_data[symbol] = price
            if platform is not None and platform["name"] == "Ethereum":
                address = platform["token_address"].lower()
                cap_data[address] = int(market_cap)
                price_data[symbol] = price

    MARKET_CAPS = cap_data
    PRICES = price_data


def marketcap(coin):
    cap = None
    if coin["type"] == "erc20":
        address = coin["address"].lower()
        return MARKET_CAPS.get(address)

    if "coinmarketcap_alias" in coin:
        cap = MARKET_CAPS.get(coin["coinmarketcap_alias"])
    if cap is None:
        slug = coin["name"].replace(" ", "-").lower()
        cap = MARKET_CAPS.get(slug)
    if cap is None:
        cap = MARKET_CAPS.get(coin["shortcut"].lower())
    return cap


def fiat_price(coin_symbol):
    return PRICES.get(coin_symbol)
