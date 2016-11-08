import binascii
from decimal import Decimal
import requests
import json
from . import types_pb2 as proto_types


class TxApi(object):

    def __init__(self, network, url):
        self.network = network
        self.url = url

    def fetch_json(self, url, resource, resourceid):
        cachefile = '%s_%s_%s' % (self.network, resource, resourceid)
        try: # looking into cache first
            j = json.load(open('txcache/' + cachefile))
            return j
        except:
            pass
        try:
            r = requests.get('%s/%s/%s' % (self.url, resource, resourceid), headers={'User-agent': 'Mozilla/5.0'})
            j = r.json()
        except:
            raise Exception('URL error: %s' % url)
        try: # saving into cache
            json.dump(j, open('txcache/' + cachefile, 'w'))
        except:
            pass
        return j

    def get_tx(self, txhash):
        raise NotImplementedError


class TxApiInsight(TxApi):

    def __init__(self, network, url, zcash=None):
        super(TxApiInsight, self).__init__(network, url)
        self.zcash = zcash

    def get_tx(self, txhash):

        data = self.fetch_json(self.url, 'tx', txhash)

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

        if self.zcash:
            if t.version == 2:
                joinsplit_cnt = len(data['vjoinsplit'])
                if joinsplit_cnt == 0:
                    t.extra_data =b'\x00'
                else:
                    extra_data_len = 1 + joinsplit_cnt * 1802 + 32 + 64 # we assume cnt < 253, so we can treat varIntLen(cnt) as 1
                    raw = fetch_json(self.url, 'rawtx', txhash)
                    raw = binascii.unhexlify(raw['rawtx'])
                    t.extra_data = raw[-extra_data_len:]

        return t


class TxApiSmartbit(TxApi):

    def get_tx(self, txhash):

        data = self.fetch_json(self.url, 'tx', txhash)

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


TxApiBitcoin = TxApiInsight(network='insight_bitcoin', url='https://insight.bitpay.com/api/')
TxApiTestnet = TxApiInsight(network='insight_testnet', url='https://test-insight.bitpay.com/api/')
TxApiSegnet = TxApiSmartbit(network='smartbit_segnet', url='https://segnet-api.smartbit.com.au/v1/blockchain/')
TxApiZcashTestnet = TxApiInsight(network='insight_zcashtestnet', url='https://explorer.testnet.z.cash/api/', zcash=True)
