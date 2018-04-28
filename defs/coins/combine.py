#!/usr/bin/env python3

import json
import glob
import re
from hashlib import sha256
import ed25519


def check_type(val, types, nullable=False, empty=False, regex=None, choice=None):
    # check nullable
    if nullable and val is None:
        return True
    # check empty
    try:
        if not empty and len(val) == 0:
            return False
    except TypeError:
        pass
    # check regex
    if regex is not None:
        if types is not str:
            return False
        m = re.match(regex, val)
        if not m:
            return False
    # check choice
    if choice is not None:
        if val not in choice:
            return False
    # check type
    if isinstance(types, list):
        return True in [isinstance(val, t) for t in types]
    else:
        return isinstance(val, types)


def validate_coin(coin):
    assert check_type(coin['coin_name'], str, regex=r'^[A-Z]')
    assert check_type(coin['coin_shortcut'], str, regex=r'^[A-Zt][A-Z][A-Z]+$')
    assert check_type(coin['coin_label'], str, regex=r'^[A-Z]')
    assert check_type(coin['website'], str, regex=r'^http.*[^/]$')
    assert check_type(coin['github'], str, regex=r'^https://github.com/.*[^/]$')
    assert check_type(coin['maintainer'], str)
    assert check_type(coin['curve_name'], str, choice=['secp256k1', 'secp256k1_decred', 'secp256k1_groestl'])
    assert check_type(coin['address_type'], int)
    assert check_type(coin['address_type_p2sh'], int)
    assert coin['address_type'] != coin['address_type_p2sh']
    assert check_type(coin['maxfee_kb'], int)
    assert check_type(coin['minfee_kb'], int)
    assert coin['maxfee_kb'] >= coin['minfee_kb']
    assert check_type(coin['hash_genesis_block'], str, regex=r'^[0-9a-f]{64}$')
    assert check_type(coin['xprv_magic'], str, regex=r'^[0-9a-f]{8}$')
    assert check_type(coin['xpub_magic'], str, regex=r'^[0-9a-f]{8}$')
    assert check_type(coin['xpub_magic_segwit_p2sh'], str, regex=r'^[0-9a-f]{8}$', nullable=True)
    assert check_type(coin['xpub_magic_segwit_native'], str, regex=r'^[0-9a-f]{8}$', nullable=True)
    assert coin['xprv_magic'] != coin['xpub_magic']
    assert coin['xprv_magic'] != coin['xpub_magic_segwit_p2sh']
    assert coin['xprv_magic'] != coin['xpub_magic_segwit_native']
    assert coin['xpub_magic'] != coin['xpub_magic_segwit_p2sh']
    assert coin['xpub_magic'] != coin['xpub_magic_segwit_native']
    assert coin['xpub_magic_segwit_p2sh'] is None or coin['xpub_magic_segwit_native'] is None or coin['xpub_magic_segwit_p2sh'] != coin['xpub_magic_segwit_native']
    assert check_type(coin['slip44'], int)
    assert check_type(coin['segwit'], bool)
    assert check_type(coin['decred'], bool)
    assert check_type(coin['forkid'], int, nullable=True)
    assert check_type(coin['force_bip143'], bool)
    assert check_type(coin['default_fee_b'], dict)
    assert check_type(coin['dust_limit'], int)
    assert check_type(coin['blocktime_seconds'], int)
    assert check_type(coin['signed_message_header'], str)
    assert check_type(coin['address_prefix'], str, regex=r'^.*:$')
    assert check_type(coin['min_address_length'], int)
    assert check_type(coin['max_address_length'], int)
    assert coin['max_address_length'] >= coin['min_address_length']
    assert check_type(coin['bech32_prefix'], str, nullable=True)
    assert check_type(coin['cashaddr_prefix'], str, nullable=True)
    assert check_type(coin['bitcore'], list, empty=True)
    for bc in coin['bitcore']:
        assert not bc.endswith('/')


def serialize(coin):
    # TODO: replace with protobuf serialization
    return json.dumps(coin).encode()


def sign(data):
    h = sha256(data).digest()
    sign_key = ed25519.SigningKey(b'A' * 32)
    return sign_key.sign(h)


def process_json(fn):
    print(fn, end=' ... ')
    j = json.load(open(fn))
    validate_coin(j)
    ser = serialize(j)
    sig = sign(ser)
    definition = (sig + ser).hex()
    print('OK')
    return j, definition


coins = {}
defs = {}
for fn in glob.glob('*.json'):
    c, d = process_json(fn)
    n = c['coin_name']
    coins[n] = c
    defs[n] = d


json.dump(coins, open('../coins.json', 'w'), indent=4, sort_keys=True)
json.dump(defs, open('../coindefs.json', 'w'), indent=4, sort_keys=True)
