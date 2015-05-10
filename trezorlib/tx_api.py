import binascii
import urllib2
import json
from decimal import Decimal
from filecache import filecache, DAY
import types_pb2 as proto_types

def insight_tx(url, rawdata=False):
    if not rawdata:
        try:
            f = urllib2.urlopen(url)
            data = json.load(f)
        except:
            raise Exception('URL error: %s' % url)
    else:
        data = url

    t = proto_types.TransactionType()
    t.version = data['version']
    t.lock_time = data['locktime']

    for vin in data['vin']:
        i = t.inputs.add()
        if 'coinbase' in vin.keys():
            i.prev_hash = "\0"*32
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

    return t

class TXAPIBitcoin(object):

    @filecache(DAY)
    def get_tx(self, txhash):
        url = 'https://insight.bitpay.com/api/tx/%s' % txhash
        return insight_tx(url)

class TXAPITestnet(object):

    @filecache(DAY)
    def get_tx(self, txhash):
        url = 'https://test-insight.bitpay.com/api/tx/%s' % txhash
        return insight_tx(url)
