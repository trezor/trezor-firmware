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
        out['type'] = 'blockchain'

        set_default(out, 'name', coin['coin_label'])
        set_default(out, 't1_enabled', 'yes')
        set_default(out, 't2_enabled', 'yes')
        update_marketcap(out, coin['coin_label'])

        #pprint.pprint(coin)

def update_erc20(details):
    networks = [
        ('eth', 1),
        # ('exp', 2),
        # ('rop', 3),
        ('rin', 4),
        ('ubq', 8),
        # ('rsk', 30),
        ('kov', 42),
        ('etc', 61),
    ]

    # Fetch list of tokens already included in Trezor Core
    r = requests.get('https://raw.githubusercontent.com/trezor/trezor-core/master/src/apps/ethereum/tokens.py')
    d = {}
    exec(r.text, d)

    # TODO 'Qmede...' can be removed after ipfs_hash is being generated into tokens.py
    ipfs_hash = d.get('ipfs_hash') or 'QmedefcF1fecLVpRymJJmyJFRpJuCTiNfPYBhzUdHPUq3T'

    infos = {}
    for n in networks:
        print("Updating info about erc20 tokens for", n[0])
        url = 'https://gateway.ipfs.io/ipfs/%s/%s.json' % (ipfs_hash, n[0])
        r = requests.get(url)
        infos[n[0]] = r.json()

    #print(infos)

    for t in d['tokens']:
        token = t[2]
        print('Updating', token)

        try:
            network = [ n[0] for n in networks if n[1] == t[0] ][0]
        except:
            raise Exception("Unknown network", t[0], "for erc20 token", token)

        try:
            info = [ i for i in infos[network] if i['symbol'] == token ][0]
        except:
            raise Exception("Unknown details for erc20 token", token)

        out = details['coins'].setdefault(token, {})
        out['name'] = info['name']
        out['type'] = 'erc20'
        out['network'] = network
        out['address'] = info['address']
        set_default(out, 't1_enabled', 'yes')
        set_default(out, 't2_enabled', 'yes')
        set_default(out, 'links', {})

        if info['website']:
            out['links']['Homepage'] = info['website']
        if info.get('social', {}).get('github', None):
            out['links']['Github'] = info['social']['github']

def update_ethereum(details):
    print('Updating Ethereum ETH')
    out = details['coins'].setdefault('ETH', {})
    out['name'] = 'Ethereum'
    out['type'] = 'coin'
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'ethereum')

def update_mosaics(details):
    r = requests.get('https://raw.githubusercontent.com/trezor/trezor-mcu/master/firmware/nem_mosaics.json')
    for mosaic in r.json():
        print('Updating', mosaic['name'], mosaic['ticker'])

        out = details['coins'].setdefault(mosaic['ticker'].strip(), {})
        out['name'] = mosaic['name']
        out['type'] = 'mosaic'
        set_default(out, 't1_enabled', 'yes')
        set_default(out, 't2_enabled', 'yes')

    # Update NEM marketcap
    update_marketcap(details['coins']['XEM'], 'NEM')

if __name__ == '__main__':
    try:
        details = json.load(open('coins_details.json', 'r'))
    except FileNotFoundError:
        details = {'coins': {}, 'info': {}}

    update_coins(details)
    update_erc20(details)
    update_ethereum(details)
    update_mosaics(details)
    update_info(details)

    print(json.dumps(details, sort_keys=True, indent=4))
    json.dump(details, open('coins_details.json', 'w'), sort_keys=True, indent=4)
