#!/usr/bin/env python3
import sys
import os
import json
import re


def get_tokens():
    tokens = []
    for s, i in networks:
        try:
            files = os.scandir('../defs/ethereum/tokens/tokens/%s' % s)
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
    count = 0
    for t in sorted(tokens, key=lambda x: x['chain'] + x['symbol'].upper()):
        address, name, symbol, decimal, chain, chain_id = t['address'], t['name'], t['symbol'], int(t['decimals']), t['chain'], t['chain_id']  # noqa:E501
        address = '\\x'.join([address[i:i + 2] for i in range(0, len(address), 2)])[2:].lower()  # noqa:E501
        ascii_only = re.match(r'^[ -\x7F]+$', symbol) is not None
        if not ascii_only:  # skip Unicode symbols, they are stupid
            continue
        name = name.strip()
        count += 1
        if python:
            print("    (%d, b'%s', '%s', %d),  # %s / %s" % (chain_id, address, symbol, decimal, chain, name))  # noqa:E501
        else:
            print('\t{%2d, "%s", " %s", %d}, // %s / %s' % (chain_id, address, symbol, decimal, chain, name))  # noqa:E501
    return count


# disabled are networks with no tokens defined in ethereum-lists/tokens repo

networks = [
    ('ella', 64),
    ('etc', 61),
    ('eth', 1),
    ('kov', 42),
    ('rin', 4),
    ('rop', 3),
    ('ubq', 8),
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
