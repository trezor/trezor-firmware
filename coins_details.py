#!/usr/bin/env python3
"""Fetch information about coins and tokens supported by Trezor and update it in coins_details.json."""
import time
import json
import requests
import pprint
import ethereum_tokens_gen

COINS = {}

def coinmarketcap_init():
    global COINS

    try:
        COINS = json.load(open('coinmarketcap.json', 'r'))
    except FileNotFoundError:
        pass
    else:
        if COINS["1"]["last_updated"] > time.time() - 3600:
            print("Using local cache of coinmarketcap")
            return

    print("Updating coins from coinmarketcap")
    total = None
    COINS = {}

    while total is None or len(COINS) < total:
        url = 'https://api.coinmarketcap.com/v2/ticker/?start=%d&convert=USD&limit=100' % (len(COINS)+1)
        data = requests.get(url).json()
        COINS.update(data['data'])
        if total is None:
            total = data['metadata']['num_cryptocurrencies']

        print("Fetched %d of %d coins" % (len(COINS), total))
        time.sleep(1)

    json.dump(COINS, open('coinmarketcap.json', 'w'), sort_keys=True, indent=4)


def coinmarketcap_info(shortcut):
    global COINS
    shortcut = shortcut.replace(' ', '-').lower()

    for _id in COINS:
        coin = COINS[_id]
        #print(shortcut, coin['website_slug'])
        if shortcut == coin['website_slug']:
            #print(coin)
            return coin

def update_marketcap(obj, shortcut):
    try:
        obj['marketcap_usd'] = int(float(coinmarketcap_info(shortcut)['quotes']['USD']['market_cap']))
    except:
        pass
        # print("Marketcap info not found for", shortcut)

def coinmarketcap_global():
    url = 'https://api.coinmarketcap.com/v2/global'
    ret = requests.get(url)
    data = ret.json()
    return data

def set_default(obj, key, default_value):
    obj[key] = obj.setdefault(key, default_value)

def update_info(details):
    details['info']['updated_at'] = int(time.time())
    details['info']['updated_at_readable'] = time.asctime()

    details['info']['t1_coins'] = len([True for _, c in details['coins'].items() if c['t1_enabled'] == 'yes' and not c.get('hidden', False)])
    details['info']['t2_coins'] = len([True for _, c in details['coins'].items() if c['t2_enabled'] == 'yes' and not c.get('hidden', False)])

    try:
        details['info']['total_marketcap_usd'] = int(coinmarketcap_global()['data']['quotes']['USD']['total_market_cap'])
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
    networks = ['eth',
        'exp',
        # 'rop',
        # 'rin',
        'ubq',
        # 'rsk',
        # 'kov',
        'etc',
    ]

    LATEST_T1 = 'https://raw.githubusercontent.com/trezor/trezor-mcu/v1.6.1/firmware/ethereum_tokens.c'
    LATEST_T2 = 'https://raw.githubusercontent.com/trezor/trezor-core/v2.0.6/src/apps/ethereum/tokens.py'

    tokens = ethereum_tokens_gen.get_tokens()
    tokens_t1 = requests.get(LATEST_T1).text
    tokens_t2 = requests.get(LATEST_T2).text

    supported = []
    for t in tokens:
        # print('Updating', t['symbol'])

        if t['chain'] not in networks:
            print('Skipping, %s is disabled' % t['chain'])
            continue

        key = "erc20:%s:%s" % (t['chain'], t['symbol'])
        supported.append(key)
        out = details['coins'].setdefault(key, {})
        out['type'] = 'erc20'
        out['network'] = t['chain']
        out['address'] = t['address']

        set_default(out, 'shortcut', t['symbol'])
        set_default(out, 'name', t['name'])
        set_default(out, 'links', {})

        if "\" %s\"" % t['symbol'] in tokens_t1:
            out['t1_enabled'] = 'yes'
        else:
            out['t1_enabled'] = 'soon'

        if "'%s'" % t['symbol'] in tokens_t2:
            out['t2_enabled'] = 'yes'
        else:
            out['t2_enabled'] = 'soon'

        out['links']['MyCrypto Wallet'] = 'https://mycrypto.com'
        out['links']['MyEtherWallet'] = 'https://www.myetherwallet.com'

        if t['website']:
            out['links']['Homepage'] = t['website']
        if t.get('social', {}).get('github', None):
            out['links']['Github'] = t['social']['github']

        update_marketcap(out, out.get('coinmarketcap_alias', t['symbol']))

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

    out = details['coins'].setdefault('coin2:ELLA', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'ELLA')
    set_default(out, 'name', 'Ellaism')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'ellaism')

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

    ut = details['coins'].setdefault('coin2:EOSC', {})
    out['type'] = 'coin'
    set_default(out, 'shortcut', 'EOSC')
    set_default(out, 'name', 'EOS Classic')
    set_default(out, 't1_enabled', 'yes')
    set_default(out, 't2_enabled', 'yes')
    update_marketcap(out, 'eosc')

def update_mosaics(details):
    d = json.load(open('defs/nem/nem_mosaics.json'))
    supported = []
    for mosaic in d:
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
        hide = False

        if 'links' not in coin:
            print("%s: Missing links" % k)
            hide = True
        if 'Homepage' not in coin['links']:
            print("%s: Missing homepage" % k)
            hide = True
        if coin['t1_enabled'] not in ('yes', 'no', 'planned', 'soon'):
            print("%s: Unknown t1_enabled" % k)
            hide = True
        if coin['t2_enabled'] not in ('yes', 'no', 'planned', 'soon'):
            print("%s: Unknown t2_enabled" % k)
            hide = True
        if 'TREZOR Wallet' in coin['links'] and coin['links']['TREZOR Wallet'] != 'https://wallet.trezor.io':
            print("%s: Strange URL for TREZOR Wallet" % k)
            hide = True

        for w in [ x.lower() for x in coin['links'].keys() ]:
            if 'wallet' in w or 'electrum' in w:
                break
        else:
            if coin['t1_enabled'] == 'yes' or coin['t2_enabled'] == 'yes':
                print("%s: Missing wallet" % k)
                hide = True
            else:
                print("%s: Missing wallet, but not hiding" % k)

        if hide:
            # If any of important detail is missing, hide coin from list
            coin['hidden'] = 1

        if not hide and coin.get('hidden'):
            print("%s: Details are OK, but coin is still hidden" % k)

    for k in details['coins'].keys():
        if details['coins'][k].get('hidden') == 1:
            print("%s: Coin is hidden" % k)

if __name__ == '__main__':
    try:
        details = json.load(open('coins_details.json', 'r'))
    except FileNotFoundError:
        details = {'coins': {}, 'info': {}}

    coinmarketcap_init()
    update_coins(details)
    update_erc20(details)
    update_ethereum(details)
    update_mosaics(details)
    update_info(details)
    check_missing_details(details)

    print(json.dumps(details['info'], sort_keys=True, indent=4))
    json.dump(details, open('coins_details.json', 'w'), sort_keys=True, indent=4)
