#!/usr/bin/env python3
"""Fetch information about coins and tokens supported by Trezor and update it in coins_details.json."""
import os
import time
import json
import logging
import requests
import sys
import coin_info

import click

LOG = logging.getLogger(__name__)

OPTIONAL_KEYS = ("links", "notes", "wallet")
ALLOWED_SUPPORT_STATUS = ("yes", "no", "planned", "soon")

OVERRIDES = coin_info.load_json("coins_details.override.json")
VERSIONS = coin_info.latest_releases()

COINMAKETCAP_CACHE = os.path.join(os.path.dirname(__file__), "coinmarketcap.json")
COINMARKETCAP_API_BASE = "https://pro-api.coinmarketcap.com/v1/"

MARKET_CAPS = {}


def coinmarketcap_call(endpoint, api_key, params=None):
    url = COINMARKETCAP_API_BASE + endpoint
    r = requests.get(url, params=params, headers={"X-CMC_PRO_API_KEY": api_key})
    r.raise_for_status()
    return r.json()


def coinmarketcap_init(api_key, refresh=None):
    global MARKET_CAPS

    force_refresh = refresh is True
    disable_refresh = refresh is False
    try:
        mtime = os.path.getmtime(COINMAKETCAP_CACHE)
        cache_is_fresh = mtime > time.time() - 3600
        if disable_refresh or (cache_is_fresh and not force_refresh):
            print("Using cached market cap data")
            with open(COINMAKETCAP_CACHE) as f:
                coinmarketcap_data = json.load(f)
        else:
            print("Fetching market cap data")
            coinmarketcap_data = coinmarketcap_call(
                "cryptocurrency/listings/latest",
                api_key,
                params={"limit": 5000, "convert": "USD"},
            )
            with open(COINMAKETCAP_CACHE, "w") as f:
                json.dump(coinmarketcap_data, f)
    except Exception as e:
        raise RuntimeError("market cap data unavailable") from e

    coin_data = {}
    for coin in coinmarketcap_data["data"]:
        slug = coin["slug"]
        market_cap = coin["quote"]["USD"]["market_cap"]
        if market_cap is not None:
            coin_data[slug] = int(market_cap)

    MARKET_CAPS = coin_data

    return coin_data


def marketcap(coin):
    cap = None
    if "coinmarketcap_alias" in coin:
        cap = MARKET_CAPS.get(coin["coinmarketcap_alias"])
    if cap is None:
        slug = coin["name"].replace(" ", "-").lower()
        cap = MARKET_CAPS.get(slug)
    if cap is None:
        cap = MARKET_CAPS.get(coin["shortcut"].lower())
    return cap


def update_marketcaps(coins):
    for coin in coins.values():
        coin["marketcap_usd"] = marketcap(coin) or 0


def summary(coins, api_key):
    t1_coins = 0
    t2_coins = 0
    supported_marketcap = 0
    for coin in coins.values():
        if coin.get("hidden"):
            continue

        t1_enabled = coin["t1_enabled"] == "yes"
        t2_enabled = coin["t2_enabled"] == "yes"
        if t1_enabled:
            t1_coins += 1
        if t2_enabled:
            t2_coins += 1
        if t1_enabled or t2_enabled:
            supported_marketcap += coin.get("marketcap_usd", 0)

    total_marketcap = None
    try:
        ret = coinmarketcap_call("global-metrics/quotes/latest", api_key)
        total_marketcap = int(ret["data"]["quote"]["USD"]["total_market_cap"])
    except:
        pass

    return dict(
        updated_at=int(time.time()),
        updated_at_readable=time.asctime(),
        t1_coins=t1_coins,
        t2_coins=t2_coins,
        marketcap_usd=supported_marketcap,
        total_marketcap_usd=total_marketcap,
    )


def _is_supported(support, trezor_version):
    version = VERSIONS[trezor_version]
    nominal = support.get(trezor_version)
    if nominal is None:
        return "no"
    elif isinstance(nominal, bool):
        return "yes" if nominal else "no"

    try:
        nominal_version = tuple(map(int, nominal.split(".")))
        return "yes" if nominal_version <= version else "soon"
    except ValueError:
        return nominal


def _webwallet_support(coin, support):
    """Check the "webwallet" support property.
    If set, check that at least one of the backends run on trezor.io.
    If yes, assume we support the coin in our wallet.
    Otherwise it's probably working with a custom backend, which means don't
    link to our wallet.
    """
    if not support.get("webwallet"):
        return False
    return any(".trezor.io" in url for url in coin["blockbook"] + coin["bitcore"])


def update_simple(coins, support_info, type):
    res = {}
    for coin in coins:
        key = coin["key"]
        support = support_info[key]

        details = dict(
            name=coin["name"],
            shortcut=coin["shortcut"],
            type=type,
            t1_enabled=_is_supported(support, "trezor1"),
            t2_enabled=_is_supported(support, "trezor2"),
        )
        for k in OPTIONAL_KEYS:
            if k in coin:
                details[k] = coin[k]

        res[key] = details

    return res


def update_bitcoin(coins, support_info):
    res = update_simple(coins, support_info, "coin")
    for coin in coins:
        key = coin["key"]
        support = support_info[key]
        details = dict(
            name=coin["coin_label"],
            links=dict(Homepage=coin["website"], Github=coin["github"]),
            wallet={},
        )
        if _webwallet_support(coin, support):
            details["wallet"]["Trezor"] = "https://wallet.trezor.io"

        res[key].update(details)

    return res


def update_erc20(coins, support_info):
    # TODO skip disabled networks?
    res = update_simple(coins, support_info, "erc20")
    for coin in coins:
        key = coin["key"]
        details = dict(
            network=coin["chain"],
            address=coin["address"],
            shortcut=coin["shortcut"],
            links={},
            wallet=dict(
                MyCrypto="https://mycrypto.com",
                MyEtherWallet="https://www.myetherwallet.com",
            ),
        )
        if coin.get("website"):
            details["links"]["Homepage"] = coin["website"]
        if coin.get("social", {}).get("github"):
            details["links"]["Github"] = coin["social"]["github"]

        res[key].update(details)

    return res


def update_ethereum_networks(coins, support_info):
    res = update_simple(coins, support_info, "coin")
    for coin in coins:
        key = coin["key"]
        details = dict(
            wallet=dict(
                MyCrypto="https://mycrypto.com",
                MyEtherWallet="https://www.myetherwallet.com",
            ),
            links=dict(Homepage=coin.get("url")),
        )
        res[key].update(details)

    return res


def check_missing_data(coins):
    for k, coin in coins.items():
        hide = False

        if "Homepage" not in coin.get("links", {}):
            level = logging.WARNING
            if k.startswith("erc20:"):
                level = logging.INFO
            LOG.log(level, f"{k}: Missing homepage")
            hide = True
        if coin["t1_enabled"] not in ALLOWED_SUPPORT_STATUS:
            LOG.warning(f"{k}: Unknown t1_enabled")
            hide = True
        if coin["t2_enabled"] not in ALLOWED_SUPPORT_STATUS:
            LOG.warning(f"{k}: Unknown t2_enabled")
            hide = True
        if (
            "Trezor" in coin.get("wallet", {})
            and coin["wallet"]["Trezor"] != "https://wallet.trezor.io"
        ):
            LOG.warning(f"{k}: Strange URL for Trezor Wallet")
            hide = True

        if coin["t1_enabled"] == "no" and coin["t2_enabled"] == "no":
            LOG.info(f"{k}: Coin not enabled on either device")
            hide = True

        if len(coin.get("wallet", {})) == 0:
            LOG.debug(f"{k}: Missing wallet")

        if "Testnet" in coin["name"]:
            LOG.debug(f"{k}: Hiding testnet")
            hide = True

        if not hide and coin.get("hidden"):
            LOG.info(f"{k}: Details are OK, but coin is still hidden")

        if hide:
            coin["hidden"] = 1

    # summary of hidden coins
    for k, coin in coins.items():
        if coin.get("hidden"):
            LOG.debug(f"{k}: Coin is hidden")


def apply_overrides(coins):
    for key, override in OVERRIDES.items():
        if key not in coins:
            LOG.warning(f"override without coin: {key}")
            continue

        def recursive_update(orig, new):
            if isinstance(new, dict) and isinstance(orig, dict):
                for k, v in new.items():
                    orig[k] = recursive_update(orig.get(k), v)
                return orig
            else:
                return new

        coin = coins[key]
        recursive_update(coin, override)


@click.command()
# fmt: off
@click.option("-r", "--refresh", "refresh", flag_value=True, default=None, help="Force refresh market cap info")
@click.option("-R", "--no-refresh", "refresh", flag_value=False, default=None, help="Force use cached market cap info")
@click.option("-A", "--api-key", required=True, envvar="COINMARKETCAP_API_KEY", help="Coinmarketcap API key")
@click.option("-v", "--verbose", is_flag=True, help="Display more info")
# fmt: on
def main(refresh, api_key, verbose):
    # setup logging
    log_level = logging.DEBUG if verbose else logging.WARNING
    root = logging.getLogger()
    root.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    root.addHandler(handler)

    coinmarketcap_init(api_key, refresh=refresh)

    defs = coin_info.coin_info()
    support_info = coin_info.support_info(defs)

    coins = {}
    coins.update(update_bitcoin(defs.bitcoin, support_info))
    coins.update(update_erc20(defs.erc20, support_info))
    coins.update(update_ethereum_networks(defs.eth, support_info))
    coins.update(update_simple(defs.nem, support_info, "mosaic"))
    coins.update(update_simple(defs.misc, support_info, "coin"))

    apply_overrides(coins)
    update_marketcaps(coins)
    check_missing_data(coins)

    info = summary(coins, api_key)
    details = dict(coins=coins, info=info)

    print(json.dumps(info, sort_keys=True, indent=4))
    with open(os.path.join(coin_info.DEFS_DIR, "coins_details.json"), "w") as f:
        json.dump(details, f, sort_keys=True, indent=4)


if __name__ == "__main__":
    main()
