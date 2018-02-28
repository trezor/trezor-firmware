#!/usr/bin/env python3
import sys
import requests


def get_tokens(ipfs_hash, chain):
    URL = 'https://gateway.ipfs.io/ipfs/%s/%s.json' % (ipfs_hash, chain)
    r = requests.get(URL)
    return r.json()


def print_tokens(ipfs_hash, chain, chain_id, python=False):
    tokens = get_tokens(ipfs_hash, chain)
    if len(tokens) > 0:
        if python:
            print('    # %s' % chain)
        else:
            print('\t// %s' % chain)
    for t in sorted(tokens, key=lambda x: x['symbol'].upper()):
        address, name, symbol, decimal = t['address'], t['name'], t['symbol'], int(t['decimals'])
        address = '\\x'.join([address[i:i + 2] for i in range(0, len(address), 2)])[2:].lower()
        if python:
            print("    (%d, b'%s', '%s', %d),  # %s" % (chain_id, address, symbol, decimal, name))
        else:
            print('\t{%2d, "%s", " %s", %d}, // %s' % (chain_id, address, symbol, decimal, name))

    return len(tokens)


# disabled are networks with no tokens defined in ethereum-lists/tokens repo

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


def generate_c(ipfs_hash):
    count = 0
    for s, i in networks:
        count += print_tokens(ipfs_hash, s, i)
    print('-' * 32)
    print('#define TOKENS_COUNT %d' % count)


def generate_python(ipfs_hash):
    print('tokens = [')
    for s, i in networks:
        print_tokens(ipfs_hash, s, i, python=True)
    print(']')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: ethereum_tokens-gen.py ipfs_hash [--python]')
        sys.exit(1)
    ipfs_hash = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == '--python':
        generate_python(ipfs_hash)
    else:
        generate_c(ipfs_hash)
