#!/usr/bin/env python3
import sys
import requests

subst = {
    (1, 'AVA \U0001F434'): 'AVA',
    (1, 'BeerCoin \U0001F37A '): 'BEER',
    (1, 'CryptoCarbon'): 'CCRB',
    (1, 'DGX 1.0'): 'DGX1',
    (1, 'JetCoins'): 'JTC',
    (1, 'Unicorn \U0001F984'): 'UNCRN',
    (1, '\U00002600\U0000FE0F PLASMA'): 'PLASMA',
    (3, '\U0001F4A5 PLASMA'): 'PLASMA',
    (4, '\U0000263C PLASMA'): 'PLASMA',
    (42, '\U0001F4A5 PLASMA'): 'PLASMA',
}


def get_tokens(chain):
    URL = 'https://raw.githubusercontent.com/kvhnuke/etherwallet/mercury/app/scripts/tokens/%sTokens.json' % chain
    r = requests.get(URL)
    return r.json()


def print_tokens(chain, chain_id, python=False):
    tokens = get_tokens(chain)
    if len(tokens) > 0:
        if python:
            print('    # %s' % chain)
        else:
            print('\t// %s' % chain)
    for t in sorted(tokens, key=lambda x: x['symbol'].upper()):
        address, symbol, decimal = t['address'], t['symbol'], int(t['decimal'])
        s = (chain_id, symbol)
        if s in subst:
            symbol = subst[s]
        address = '\\x'.join([address[i:i + 2] for i in range(0, len(address), 2)])[2:].lower()
        if python:
            print("    {'chain_id': %2d, 'address': b'%s', 'symbol': '%s', 'decimal': %d}," % (chain_id, address, symbol, decimal))
        else:
            print('\t{%2d, "%s", " %s", %d},' % (chain_id, address, symbol, decimal))

    return len(tokens)


networks = [
    ('eth', 1),
    ('exp', 2),
    ('ropsten', 3),
    ('rinkeby', 4),
    ('ubq', 8),
    ('rsk', 30),
    ('kovan', 42),
    ('etc', 61),
]


def generate_c():
    count = 0
    for s, i in networks:
        count += print_tokens(s, i)
    print('-' * 32)
    print('#define TOKENS_COUNT %d' % count)


def generate_python():
    print('tokens = [')
    for s, i in networks:
        print_tokens(s, i, python=True)
    print(']')

if  __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--python':
        generate_python()
    else:
        generate_c()
