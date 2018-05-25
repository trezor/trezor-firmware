#!/usr/bin/env python3
import sys
import os
import json

def get_tokens():
    tokens = []
    for s, i in networks:
        try:
            files = os.scandir('defs/ethereum/tokens/tokens/%s' % s)
        except FileNotFoundError:
            continue

        for f in files:
            if not f.path.endswith('.json'):
                continue

            # print('Processing', f.path)
            data = json.load(open(f.path, 'r'))
            data['chain'] = s
            data['chain_id'] = i
            tokens.append(data)

    return tokens


def print_tokens(tokens, python=False):
    for t in sorted(tokens, key=lambda x: x['chain'] + x['symbol'].upper()):
        address, name, symbol, decimal, chain, chain_id = t['address'], t['name'], t['symbol'], int(t['decimals']), t['chain'], t['chain_id']
        address = '\\x'.join([address[i:i + 2] for i in range(0, len(address), 2)])[2:].lower()
        if python:
            print("    (%d, b'%s', '%s', %d),  # %s / %s" % (chain_id, address, symbol, decimal, chain, name))
        else:
            print('\t{%2d, "%s", " %s", %d}, // %s / %s' % (chain_id, address, symbol, decimal, chain, name))

    return len(tokens)


# disabled are networks with no tokens defined in ethereum-lists/tokens repo

networks = [
    ('eth', 1),
    ('exp', 2),
    # ('rop', 3),
    # ('rin', 4),
    ('ubq', 8),
    # ('rsk', 30),
    # ('kov', 42),
    ('etc', 61),
]


def generate_c(tokens):
    count = print_tokens(tokens)
    print('-' * 32)
    print('#define TOKENS_COUNT %d' % count)


def generate_python(tokens):
    print('tokens = [')
    print_tokens(tokens, python=True)
    print(']')


if __name__ == '__main__':
    tokens = get_tokens()

    if len(sys.argv) > 1 and sys.argv[1] == '--python':
        generate_python(tokens)
    else:
        generate_c(tokens)
