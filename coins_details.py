#!/usr/bin/env python3
"""Fetch information about coins and tokens supported by Trezor and update it in coins_details.json."""
import time
import json
import requests
import pprint

SKIP_COINMARKETCAP = True

def coinmarketcap_info(shortcut):
    if SKIP_COINMARKETCAP:
        raise Exception("Skipping coinmarketcap call")

    shortcut = shortcut.replace(' ', '-')
    url = 'https://api.coinmarketcap.com/v1/ticker/%s/?convert=USD' % shortcut
    try:
        return requests.get(url).json()[0]
    except KeyboardInterrupt:
        raise
    except:
        print("Cannot fetch Coinmarketcap info for %s" % shortcut)

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
    details['info']['t1_coins'] = len([True for _, c in details['coins'].items() if c['t1_enabled'] == 'yes'])
    details['info']['t2_coins'] = len([True for _, c in details['coins'].items() if c['t2_enabled'] == 'yes'])

    try:
        details['info']['total_marketcap_usd'] = int(coinmarketcap_global()['total_market_cap_usd'])
    except:
        pass

    marketcap = 0
    for k, c in details['coins'].items():
        if c['t1_enabled'] == 'yes' or c['t2_enabled'] == 'yes':
            marketcap += details['coins'][k].setdefault('marketcap_usd', 0)
    details['info']['marketcap_usd'] = marketcap

def check_unsupported(details, prefix, supported):
    for k in details['coins'].keys():
        if not k.startswith(prefix):
            continue
        if k not in supported:
            print("%s not supported by Trezor? (Possible manual entry)" % k)

def update_coins(details):
    coins = json.load(open('coins.json', 'r'))

    supported = []
    for coin in coins:
        if coin['firmware'] != 'stable':
            continue

        # print("Updating", coin['coin_label'], coin['coin_shortcut'])
        key = "coin:%s" % coin['coin_shortcut']
        supported.append(key)
        out = details['coins'].setdefault(key, {})
        out['type'] = 'coin'
        set_default(out, 'shortcut', coin['coin_shortcut'])
        set_default(out, 'name', coin['coin_label'])
        set_default(out, 'links', {})
        set_default(out, 't1_enabled', 'yes')
        set_default(out, 't2_enabled', 'yes')
        update_marketcap(out, coin.get('coinmarketcap_alias', coin['coin_label']))

    check_unsupported(details, 'coin:', supported)

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
        # print("Updating info about erc20 tokens for", n[0])
        url = 'https://gateway.ipfs.io/ipfs/%s/%s.json' % (ipfs_hash, n[0])
        r = requests.get(url)
        infos[n[0]] = r.json()

    supported = []
    for t in d['tokens']:
        token = t[2]
        # print('Updating', token)

        try:
            network = [ n[0] for n in networks if n[1] == t[0] ][0]
        except:
            raise Exception("Unknown network", t[0], "for erc20 token", token)

        try:
            info = [ i for i in infos[network] if i['symbol'] == token ][0]
        except:
            raise Exception("Unknown details for erc20 token", token)

        key = "erc20:%s:%s" % (network, token)
        supported.append(key)
        out = details['coins'].setdefault(key, {})
        out['type'] = 'erc20'
        out['network'] = network
        out['address'] = info['address']

        set_default(out, 'shortcut', token)
        set_default(out, 'name', info['name'])
        set_default(out, 't1_enabled', 'yes')
        set_default(out, 't2_enabled', 'yes')
        set_default(out, 'links', {})

        if info['website']:
            out['links']['Homepage'] = info['website']
        if info.get('social', {}).get('github', None):
            out['links']['Github'] = info['social']['github']

        update_marketcap(out, out.get('coinmarketcap_alias', token))

    check_unsupported(details, 'erc20:', supported)

def update_ethereum(details):
    out = details['coins'].setdefault('coin2:ETH', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'ETH')
    set_default(out, 'name', 'Ethereum')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'ethereum')

    out = details['coins'].setdefault('coin2:ETC', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'ETC')
    set_default(out, 'name', 'Ethereum Classic')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'ethereum-classic')

    out = details['coins'].setdefault('coin2:RSK', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'RSK')
    set_default(out, 'name', 'Rootstock')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'rootstock')

    out = details['coins'].setdefault('coin2:EXP', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'EXP')
    set_default(out, 'name', 'Expanse')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'expanse')

    out = details['coins'].setdefault('coin2:UBQ', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'UBQ')
    set_default(out, 'name', 'Ubiq')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'ubiq')

    out = details['coins'].setdefault('coin2:EGEM', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'EGEM')
    set_default(out, 'name', 'EtherGem')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'egem')

    out = details['coins'].setdefault('coin2:ETSC', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'ETSC')
    set_default(out, 'name', 'EthereumSocial')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'etsc')

def update_mosaics(details):
    r = requests.get('https://raw.githubusercontent.com/trezor/trezor-mcu/master/firmware/nem_mosaics.json')
    supported = []
    for mosaic in r.json():
        # print('Updating', mosaic['name'], mosaic['ticker'])

        key = "mosaic:%s" % mosaic['ticker'].strip()
        supported.append(key)
        out = details['coins'].setdefault(key, {})
        out['type'] = 'mosaic'
        set_default(out, 'shortcut', mosaic['ticker'].strip())
        set_default(out, 'name', mosaic['name'])
        set_default(out, 't1_enabled', 'yes')
        set_default(out, 't2_enabled', 'yes')

        update_marketcap(out, out.get('coinmarketcap_alias', out['name']))

    check_unsupported(details, 'mosaic:', supported)

def check_missing_details(details):
    for k in details['coins'].keys():
        coin = details['coins'][k]

        if 'links' not in coin:
            print("%s: Missing links" % k)
            continue
        if 'Homepage' not in coin['links']:
            print("%s: Missing homepage" % k)
        if coin['t1_enabled'] not in ('yes', 'no', 'planned', 'in progress'):
            print("%s: Unknown t1_enabled" % k)
        if coin['t2_enabled'] not in ('yes', 'no', 'planned', 'in progress'):
            print("%s: Unknown t2_enabled" % k)
        if 'TREZOR Wallet' in coin['links'] and coin['links']['TREZOR Wallet'] != 'https://wallet.trezor.io':
            print("%s: Strange URL for TREZOR Wallet" % k)

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
    check_missing_details(details)

    print(json.dumps(details['info'], sort_keys=True, indent=4))
    json.dump(details, open('coins_details.json', 'w'), sort_keys=True, indent=4)
