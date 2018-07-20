#!/usr/bin/env python3
"""Fetch information about coins and tokens supported by Trezor and update it in coins_details.json."""
import time
import json
import logging
import requests
import coin_defs

OPTIONAL_KEYS = ("links", "notes", "wallet")
OVERRIDES = coin_defs.load_json("coins_details.override.json")

VERSIONS = coin_defs.latest_releases()

COINS = {}

log = logging.getLogger(__name__)


def coinmarketcap_init():
    global COINS

    try:
        marketcap_json = json.load(open("coinmarketcap.json", "r"))
    except FileNotFoundError:
        pass
    else:
        pass
        # if COINS["1"]["last_updated"] > time.time() - 3600:
        #     print("Using local cache of coinmarketcap")
        #     return

    for coin in marketcap_json.values():
        slug = coin["website_slug"]
        market_cap = coin["quotes"]["USD"]["market_cap"]
        if market_cap is not None:
            COINS[slug] = int(float(market_cap))

    return

    print("Updating coins from coinmarketcap")
    total = None
    COINS = {}

    while total is None or len(COINS) < total:
        url = (
            "https://api.coinmarketcap.com/v2/ticker/?start=%d&convert=USD&limit=100"
            % (len(COINS) + 1)
        )
        data = requests.get(url).json()
        COINS.update(data["data"])
        if total is None:
            total = data["metadata"]["num_cryptocurrencies"]

        print("Fetched %d of %d coins" % (len(COINS), total))
        time.sleep(1)

    json.dump(COINS, open("coinmarketcap.json", "w"), sort_keys=True, indent=4)


def marketcap(coin):
    cap = None

    if "coinmarketcap_alias" in coin:
        cap = COINS.get(coin["coinmarketcap_alias"])
    
    if not cap:
        slug = coin["name"].replace(" ", "-").lower()
        cap = COINS.get(slug)
    
    if not cap:
        cap = COINS.get(coin["shortcut"].lower())
    
    return cap


def update_marketcap(coins):
    for coin in coins.values():
        cap = marketcap(coin)
        if cap:
            coin["marketcap_usd"] = cap


def coinmarketcap_global():
    url = "https://api.coinmarketcap.com/v2/global"
    ret = requests.get(url)
    data = ret.json()
    return data


def update_info(details):
    details["info"]["updated_at"] = int(time.time())
    details["info"]["updated_at_readable"] = time.asctime()

    details["info"]["t1_coins"] = len(
        [
            True
            for _, c in details["coins"].items()
            if c.get("t1_enabled") == "yes" and not c.get("hidden", False)
        ]
    )
    details["info"]["t2_coins"] = len(
        [
            True
            for _, c in details["coins"].items()
            if c.get("t2_enabled") == "yes" and not c.get("hidden", False)
        ]
    )

    try:
        details["info"]["total_marketcap_usd"] = int(
            coinmarketcap_global()["data"]["quotes"]["USD"]["total_market_cap"]
        )
    except:
        pass

    marketcap = 0
    for k, c in details["coins"].items():
        if c["t1_enabled"] == "yes" or c["t2_enabled"] == "yes":
            marketcap += details["coins"][k].setdefault("marketcap_usd", 0)
    details["info"]["marketcap_usd"] = marketcap


def check_unsupported(details, prefix, supported):
    for k in details["coins"].keys():
        if not k.startswith(prefix):
            continue
        if k not in supported:
            print("%s not supported by Trezor? (Possible manual entry)" % k)


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

        # XXX get rid of this in favor of res[key]
        res["coin:{}".format(coin["shortcut"])] = details

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

        # XXX drop newkey
        if type == "mosaic":
            newkey = "mosaic:{}".format(coin["shortcut"])
        else:
            newkey = "coin2:{}".format(coin["shortcut"])

        details = dict(
            name=coin["name"],
            shortcut=coin["shortcut"],
            type=type,
            t1_enabled=_is_supported(support, 1),
            t2_enabled=_is_supported(support, 2),
        )
        for key in OPTIONAL_KEYS:
            if key in coin:
                details[key] = coin[key]

        res[newkey] = details

    return res


def update_ethereum_networks(coins, support_info):
    res = update_simple(coins, support_info, "coin")
    for coin in coins:
        newkey = "coin2:{}".format(coin["shortcut"])
        res[newkey]["wallet"] = dict(
            MyCrypto="https://mycrypto.com",
            MyEtherWallet="https://www.myetherwallet.com",
        )
        res[newkey]["links"] = dict(Homepage=coin.get("url"))
    return res


def check_missing_details(details):
    for k in details["coins"].keys():
        coin = details["coins"][k]
        hide = False

        if "links" not in coin:
            print("%s: Missing links" % k)
            hide = True
        if "Homepage" not in coin.get("links", {}):
            print("%s: Missing homepage" % k)
            hide = True
        if coin["t1_enabled"] not in ("yes", "no", "planned", "soon"):
            print("%s: Unknown t1_enabled" % k)
            hide = True
        if coin["t2_enabled"] not in ("yes", "no", "planned", "soon"):
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

    for k in details["coins"].keys():
        if details["coins"][k].get("hidden") == 1:
            print("%s: Coin is hidden" % k)


def apply_overrides(coins):
    for key, override in OVERRIDES.items():
        if key not in coins:
            log.warning("override without coin: {}".format(key))
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
    # try:
    #     details = json.load(open('../defs/coins_details.json', 'r'))
    # except FileNotFoundError:
    #     details = {'coins': {}, 'info': {}}

    coinmarketcap_init()

    defs = coin_defs.get_all()
    all_coins = sum(defs.values(), [])
    support_info = coin_defs.support_info(all_coins, erc20_versions=VERSIONS)

    coins = {}
    coins.update(update_coins(defs["btc"], support_info))
    coins.update(update_erc20(defs["erc20"], support_info))
    coins.update(update_ethereum_networks(defs["eth"], support_info))
    coins.update(update_simple(defs["nem"], support_info, "mosaic"))
    coins.update(update_simple(defs["other"], support_info, "coin"))

    apply_overrides(coins)
    update_marketcap(coins)

    details = dict(coins=coins, info={})
    update_info(details)
    check_missing_details(details)

    print(json.dumps(details["info"], sort_keys=True, indent=4))
    json.dump(details, open("../defs/coins_details.json", "w"), sort_keys=True, indent=4)

