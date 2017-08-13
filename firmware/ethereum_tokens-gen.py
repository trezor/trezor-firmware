#!/usr/bin/env python3
import requests

subst = {
    (1, 'AVA \U0001F434'): 'AVA',
    (1, 'BeerCoin \U0001F37A '): 'BEER',
    (1, 'CryptoCarbon'): 'CCRB',
    (1, 'DGX 1.0'): 'DGX1',
    (1, 'JetCoins'): 'JTC',
    (1, 'Unicorn \U0001F984 '): 'UNCRN',
}


def get_tokens(chain):
    URL = 'https://raw.githubusercontent.com/kvhnuke/etherwallet/mercury/app/scripts/tokens/%sTokens.json' % chain
    r = requests.get(URL)
    return r.json()


def print_tokens(chain, chain_id):
    tokens = get_tokens(chain)

    for t in sorted(tokens, key=lambda x: x['symbol'].upper()):
        address, symbol, decimal = t['address'], t['symbol'], t['decimal']
        s = (chain_id, symbol)
        if s in subst:
            symbol = subst[s]
        address = '\\x'.join([address[i:i + 2] for i in range(0, len(address), 2)])[2:].lower()
        print('\t{%2d, "%s", " %s", %d},' % (chain_id, address, symbol, decimal))

    return len(tokens)


count = 0

count += print_tokens('eth', 1)
count += print_tokens('etc', 61)

print('-' * 32)

print('#define TOKENS_COUNT %d' % count)
