import binascii
from decimal import Decimal
# from filecache import filecache, DAY
import requests
from . import types_pb2 as proto_types

def fetch_json(url):
    try:
        r = requests.get(url, headers={'User-agent': 'Mozilla/5.0'})
        return r.json()
    except:
        raise Exception('URL error: %s' % url)

def insight_tx(url, rawdata=False, zcash=False):
    if not rawdata:
        data = fetch_json(url)
    else:
        data = url

    t = proto_types.TransactionType()
    t.version = data['version']
    t.lock_time = data['locktime']

    for vin in data['vin']:
        i = t.inputs.add()
        if 'coinbase' in vin.keys():
            i.prev_hash = b"\0"*32
            i.prev_index = 0xffffffff # signed int -1
            i.script_sig = binascii.unhexlify(vin['coinbase'])
            i.sequence = vin['sequence']

        else:
            i.prev_hash = binascii.unhexlify(vin['txid'])
            i.prev_index = vin['vout']
            i.script_sig = binascii.unhexlify(vin['scriptSig']['hex'])
            i.sequence = vin['sequence']

    for vout in data['vout']:
        o = t.bin_outputs.add()
        o.amount = int(Decimal(str(vout['value'])) * 100000000)
        o.script_pubkey = binascii.unhexlify(vout['scriptPubKey']['hex'])

    if zcash:
        if t.version == 2:
            joinsplit_cnt = len(data['vjoinsplit'])
            if joinsplit_cnt == 0:
                t.extra_data =b'\x00'
            else:
                extra_data_len = 1 + joinsplit_cnt * 1802 + 32 + 64 # we assume cnt < 253, so we can treat varIntLen(cnt) as 1
                raw = fetch_json(url.replace('/tx/', '/rawtx/'))
                raw = binascii.unhexlify(raw['rawtx'])
                t.extra_data = raw[-extra_data_len:]

    return t

def smartbit_tx(url, rawdata=False):
    if not rawdata:
        data = fetch_json(url)
    else:
        data = url

    data = data['transaction']

    t = proto_types.TransactionType()
    t.version = int(data['version'])
    t.lock_time = data['locktime']

    for vin in data['inputs']:
        i = t.inputs.add()
        if 'coinbase' in vin.keys():
            i.prev_hash = b"\0"*32
            i.prev_index = 0xffffffff # signed int -1
            i.script_sig = binascii.unhexlify(vin['coinbase'])
            i.sequence = vin['sequence']

        else:
            i.prev_hash = binascii.unhexlify(vin['txid'])
            i.prev_index = vin['vout']
            i.script_sig = binascii.unhexlify(vin['script_sig']['hex'])
            i.sequence = vin['sequence']

    for vout in data['outputs']:
        o = t.bin_outputs.add()
        o.amount = int(Decimal(vout['value']) * 100000000)
        o.script_pubkey = binascii.unhexlify(vout['script_pub_key']['hex'])

    return t

class TXAPIBitcoin(object):

    # @filecache(DAY)
    def get_tx(self, txhash):
        url = 'https://insight.bitpay.com/api/tx/%s' % txhash.decode('ascii')
        return insight_tx(url)


class TXAPITestnet(object):

    # @filecache(DAY)
    def get_tx(self, txhash):
        url = 'https://test-insight.bitpay.com/api/tx/%s' % txhash.decode('ascii')
        return insight_tx(url)

class TXAPISegnet(object):

    # @filecache(DAY)
    def get_tx(self, txhash):
        url = 'https://segnet-api.smartbit.com.au/v1/blockchain/tx/%s' % txhash.decode('ascii')
        return smartbit_tx(url)

class TXAPIZcashTestnet(object):

    # @filecache(DAY)
    def get_tx(self, txhash):
        url = 'https://explorer.testnet.z.cash/api/tx/%s' % txhash.decode('ascii')
        return insight_tx(url, zcash=True)
