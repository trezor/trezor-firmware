#!/usr/bin/env python3
import json


def is_hex(val):
    try:
        int(val, 16)
        return True
    except:
        return False


for coin in json.load(open('coins.json')):
    assert isinstance(coin['coin_name'], str)
    assert isinstance(coin['coin_shortcut'], str)
    assert isinstance(coin['coin_label'], str)
    assert isinstance(coin['curve_name'], str)
    assert isinstance(coin['address_type'], int)
    assert isinstance(coin['address_type_p2sh'], int)
    assert coin['address_type'] != coin['address_type_p2sh']
    assert isinstance(coin['maxfee_kb'], int)
    assert isinstance(coin['minfee_kb'], int)
    assert coin['maxfee_kb'] > coin['minfee_kb']
    assert coin['signed_message_header']
    assert is_hex(coin['hash_genesis_block'])
    assert is_hex(coin['xprv_magic'])
    assert is_hex(coin['xpub_magic'])
    assert isinstance(coin['bip44'], int)
    assert isinstance(coin['segwit'], bool)
    assert isinstance(coin['decred'], bool)
    assert coin['forkid'] is None or isinstance(coin['forkid'], int)
    assert isinstance(coin['force_bip143'], bool)
    assert coin['version_group_id'] is None or is_hex(coin['version_group_id'])
    assert isinstance(coin['default_fee_b'], dict)
    assert isinstance(coin['dust_limit'], int)
    assert isinstance(coin['blocktime_minutes'], int) or isinstance(coin['blocktime_minutes'], float)
    assert coin['firmware'] is None or coin['firmware'] in ['stable', 'debug']
    assert isinstance(coin['signed_message_header'], str)
    assert isinstance(coin['min_address_length'], int)
    assert isinstance(coin['max_address_length'], int)
    assert isinstance(coin['bitcore'], list)
    assert coin['xpub_magic_segwit_p2sh'] is None or is_hex(coin['xpub_magic_segwit_p2sh'])
    assert coin['bech32_prefix'] is None or isinstance(coin['bech32_prefix'], str)

print('OK')
