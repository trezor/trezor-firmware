import binascii
import urllib2
import json
try:
    from filecache import filecache, MONTH
except:
    def filecache(x):
        def _inner(y):
            return y
        return _inner
    MONTH = None

import types_pb2 as proto_types

def bitcore_tx(url):
    f = urllib2.urlopen(url)
    data = json.load(f)

    t = proto_types.TransactionType()
    t.version = data['version']
    t.lock_time = data['locktime']

    for vin in data['vin']:
        i = t.inputs.add()
        i.prev_hash = binascii.unhexlify(vin['txid'])
        i.prev_index = vin['vout']
        asm = [ binascii.unhexlify(x) for x in vin['scriptSig']['asm'].split(' ') ]
        i.script_sig = chr(len(asm[0])) + asm[0] + chr(len(asm[1])) + asm[1] # TODO: should be op_push(x) instead of chr(len(x))

    for vout in data['vout']:
        o = t.outputs.add()
        o.amount = int(vout['value'] * 100000000)
        asm = vout['scriptPubKey']['asm'].split(' ') # we suppose it's OP_DUP OP_HASH160 pubkey OP_EQUALVERIFY OP_CHECKSIG
        o.script_pubkey = binascii.unhexlify('76a914' + asm[2] + '88ac')

    return t

class TXAPIBitcoin(object):

    @filecache(MONTH)
    def get_tx(self, txhash):
        url = 'http://live.bitcore.io/api/tx/%s' % txhash
        return bitcore_tx(url)

class TXAPITestnet(object):

    @filecache(MONTH)
    def get_tx(self, txhash):
        url = 'http://test.bitcore.io/api/tx/%s' % txhash
        return bitcore_tx(url)
