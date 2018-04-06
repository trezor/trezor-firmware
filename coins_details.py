#!/usr/bin/env python3
"""Fetch information about coins and tokens supported by Trezor and update it in coins_details.json."""
import time
import json
import requests
import pprint

SKIP_COINMARKETCAP = False

def coinmarketcap_info(shortcut):
    if SKIP_COINMARKETCAP:
        raise Exception("Skipping coinmarketcap call")

    shortcut = shortcut.replace(' ', '-')
    url = 'https://api.coinmarketcap.com/v1/ticker/%s/?convert=USD' % shortcut
    ret = requests.get(url)
    data = ret.json()
    try:
        return data[0]
    except:
        print("Cannot fetch info for %s" % shortcut)

def update_marketcap(obj, shortcut):
    try:
        obj['marketcap_usd'] = int(float(coinmarketcap_info(shortcut)['market_cap_usd']))
    except:
        pass

def coinmarketcap_global():
    if SKIP_COINMARKETCAP:
        raise Exception("Skipping coinmarketcap call")

    url = 'https://api.coinmarketcap.com/v1/global'
    ret = requests.get(url)
    data = ret.json()
    return data

def set_default(obj, key, default_value):
    obj[key] = obj.setdefault(key, default_value)

def update_info(details):
    details['info']['updated_at'] = int(time.time())
    details['info']['updated_at_readable'] = time.asctime()
    details['info']['coins'] = len(details['coins'])
    
    try:
        details['info']['total_marketcap_usd'] = int(coinmarketcap_global()['total_market_cap_usd'])
    except:
        pass

    marketcap = 0
    for c in details['coins']:
        marketcap += details['coins'][c].setdefault('marketcap_usd', 0)
    details['info']['marketcap_usd'] = marketcap

def update_coins(details):
    coins = json.load(open('coins.json', 'r'))

    for coin in coins:
        if coin['firmware'] != 'stable':
            continue

        print("Updating", coin['coin_label'], coin['coin_shortcut'])
        out = details['coins'].setdefault(coin['coin_shortcut'], {})
        out['shortcut'] = coin['coin_shortcut']
        out['type'] = 'coin'

        set_default(out, 'name', coin['coin_label'])
        set_default(out, 't1_enabled', 'yes')
        set_default(out, 't2_enabled', 'yes')
        update_marketcap(out, coin['coin_label'])

        #pprint.pprint(coin)

def update_erc20(details):
    # FIXME Parse tokens using trezor-common/ethereum_tokens-gen.py
    r = requests.get('https://raw.githubusercontent.com/trezor/trezor-core/master/src/apps/ethereum/tokens.py')
    d = {}
    exec(r.text, d)
    for t in d['tokens']:
        token = t[2]
        print('Updating', token)

        out = details['coins'].setdefault(token, {})
        out['type'] = 'erc20'
        out['chain_id'] = t[0]
        set_default(out, 't1_enabled', 'yes')
        set_default(out, 't2_enabled', 'yes')

def update_ethereum(details):
    print('Updating Ethereum ETH')
    out = details['coins'].setdefault('ETH', {})
    out['name'] = 'Ethereum'
    out['type'] = 'coin'
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'ethereum')

def update_nem(details):
    print('Updating NEM')
    out = details['coins'].setdefault('NEM', {})
    out['name'] = 'NEM'
    out['type'] = 'coin'
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')   
    update_marketcap(out, 'nem')

if __name__ == '__main__':
    try:
        details = json.load(open('coins_details.json', 'r'))
    except FileNotFoundError:
        details = {'coins': {}, 'info': {}}

    update_coins(details)
    update_erc20(details)
    update_ethereum(details)
    update_nem(details)
    update_info(details)

    print(json.dumps(details, sort_keys=True, indent=4))
    json.dump(details, open('coins_details.json', 'w'), sort_keys=True, indent=4)
