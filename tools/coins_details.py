#!/usr/bin/env python3
"""Fetch information about coins and tokens supported by Trezor and update it in coins_details.json."""
import os
import time
import json
import logging
import requests
import coin_defs

LOG = logging.getLogger(__name__)

OPTIONAL_KEYS = ("links", "notes", "wallet")
ALLOWED_SUPPORT_STATUS = ("yes", "no", "planned", "soon")

OVERRIDES = coin_defs.load_json("coins_details.override.json")
VERSIONS = coin_defs.latest_releases()

COINMAKETCAP_CACHE = os.path.join(os.path.dirname(__file__), "coinmarketcap.json")

COINMARKETCAP_TICKERS_URL = (
    "https://api.coinmarketcap.com/v2/ticker/?start={}&convert=USD&limit=100"
)
COINMARKETCAP_GLOBAL_URL = "https://api.coinmarketcap.com/v2/global"


def coinmarketcap_init():
    try:
        mtime = os.path.getmtime(COINMAKETCAP_CACHE)
        if mtime > time.time() - 3600:
            print("Using cached market cap data")
            with open(COINMAKETCAP_CACHE) as f:
                return json.load(f)
    except Exception:
        pass

    print("Updating coins from coinmarketcap")
    total = None
    ctr = 0
    coin_data = {}

    while total is None or ctr < total:
        url = COINMARKETCAP_TICKERS_URL.format(ctr + 1)
        data = requests.get(url).json()

        if total is None:
            total = data["metadata"]["num_cryptocurrencies"]
        ctr += len(data["data"])

        for coin in data["data"].values():
            slug = coin["website_slug"]
            market_cap = coin["quotes"]["USD"]["market_cap"]
            if market_cap is not None:
                coin_data[slug] = int(market_cap)

        print("Fetched {} of {} coins".format(ctr, total))
        time.sleep(1)

    with open(COINMAKETCAP_CACHE, "w") as f:
        json.dump(coin_data, f)

    return coin_data


MARKET_CAPS = coinmarketcap_init()


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


def summary(coins):
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
        ret = requests.get(COINMARKETCAP_GLOBAL_URL).json()
        total_marketcap = int(ret["data"]["quotes"]["USD"]["total_market_cap"])
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
    version = VERSIONS[str(trezor_version)]
    nominal = support.get("trezor" + str(trezor_version))
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


def update_coins(coins, support_info):
    res = {}
    for coin in coins:
        key = coin["key"]
        support = support_info[key]
        details = dict(
            type="coin",
            shortcut=coin["shortcut"],
            name=coin["coin_label"],
            links=dict(Homepage=coin["website"], Github=coin["github"]),
            t1_enabled=_is_supported(support, 1),
            t2_enabled=_is_supported(support, 2),
            wallet={},
        )
        if _webwallet_support(coin, support):
            details["wallet"]["Trezor"] = "https://wallet.trezor.io"
        if support.get("other"):
            details["wallet"].update(support["other"])

        res[key] = details

    return res


def update_erc20(coins, support_info):
    # TODO skip disabled networks?
    res = {}
    for coin in coins:
        key = coin["key"]
        support = support_info[key]
        details = dict(
            type="erc20",
            network=coin["chain"],
            address=coin["address"],
            shortcut=coin["shortcut"],
            name=coin["name"],
            links={},
            wallet=dict(
                MyCrypto="https://mycrypto.com",
                MyEtherWallet="https://www.myetherwallet.com",
            ),
            t1_enabled=support["trezor1"],
            t2_enabled=support["trezor2"],
        )
        if coin.get("website"):
            details["links"]["Homepage"] = coin["website"]
        if coin.get("social", {}).get("github"):
            details["links"]["Github"] = coin["social"]["github"]

        res[key] = details

    return res


def update_simple(coins, support_info, type):
    res = {}
    for coin in coins:
        key = coin["key"]
        support = support_info[key]

        details = dict(
            name=coin["name"],
            shortcut=coin["shortcut"],
            type=type,
            t1_enabled=_is_supported(support, 1),
            t2_enabled=_is_supported(support, 2),
        )
        for k in OPTIONAL_KEYS:
            if k in coin:
                details[k] = coin[k]

        res[key] = details

    return res


def update_ethereum_networks(coins, support_info):
    res = update_simple(coins, support_info, "coin")
    for coin in coins:
        res[coin["key"]].update(
            wallet=dict(
                MyCrypto="https://mycrypto.com",
                MyEtherWallet="https://www.myetherwallet.com",
            ),
            links=dict(Homepage=coin.get("url")),
        )
    return res


def check_missing_data(coins):
    for k, coin in coins.items():
        hide = False

        if "Homepage" not in coin.get("links", {}):
            print("%s: Missing homepage" % k)
            hide = True
        if coin["t1_enabled"] not in ALLOWED_SUPPORT_STATUS:
            print("%s: Unknown t1_enabled" % k)
            hide = True
        if coin["t2_enabled"] not in ALLOWED_SUPPORT_STATUS:
            print("%s: Unknown t2_enabled" % k)
            hide = True
        if (
            "Trezor" in coin.get("wallet", {})
            and coin["wallet"]["Trezor"] != "https://wallet.trezor.io"
        ):
            print("%s: Strange URL for Trezor Wallet" % k)
            hide = True

        if len(coin.get("wallet", {})) == 0:
            print("%s: Missing wallet" % k)

        if "Testnet" in coin["name"]:
            print("%s: Hiding testnet" % k)
            hide = True

        if hide:
            if coin.get("hidden") != 1:
                print("%s: HIDING COIN!" % k)

            # If any of important detail is missing, hide coin from list
            coin["hidden"] = 1

        if not hide and coin.get("hidden"):
            print("%s: Details are OK, but coin is still hidden" % k)

    # summary of hidden coins
    for k, coin in coins.items():
        if coin.get("hidden") == 1:
            print("%s: Coin is hidden" % k)


def apply_overrides(coins):
    for key, override in OVERRIDES.items():
        if key not in coins:
            LOG.warning("override without coin: {}".format(key))
            continue

        def recursive_update(orig, new):
            if isinstance(new, dict) and isinstance(orig, dict):
                for k, v in new.items():
                    orig[k] = recursive_update(orig.get(k), v)
            else:
                return new

        coin = coins[key]
        recursive_update(coin, override)


if __name__ == "__main__":
    defs = coin_defs.get_all()
    all_coins = sum(defs.values(), [])
    support_info = coin_defs.support_info(all_coins, erc20_versions=VERSIONS)

    coins = {}
    coins.update(update_coins(defs["coins"], support_info))
    coins.update(update_erc20(defs["erc20"], support_info))
    coins.update(update_ethereum_networks(defs["eth"], support_info))
    coins.update(update_simple(defs["nem"], support_info, "mosaic"))
    coins.update(update_simple(defs["misc"], support_info, "coin"))

    apply_overrides(coins)
    update_marketcaps(coins)
    check_missing_data(coins)

    info = summary(coins)
    details = dict(coins=coins, info=info)

    print(json.dumps(info, sort_keys=True, indent=4))
    with open(os.path.join(coin_defs.DEFS_DIR, "coins_details.json"), "w") as f:
        json.dump(details, f, sort_keys=True, indent=4)
