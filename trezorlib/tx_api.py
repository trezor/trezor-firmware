# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
# Copyright (C) 2016      Jochen Hoenicke <hoenicke@gmail.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import binascii
from decimal import Decimal
import requests
import json

from . import messages as proto
cache_dir = None


class TxApi(object):

    def __init__(self, network, url):
        self.network = network
        self.url = url
        self.pushtx_url = url

    def get_url(self, resource, resourceid):
        url = '%s%s/%s' % (self.url, resource, resourceid)
        return url

    def fetch_json(self, resource, resourceid):
        global cache_dir
        if cache_dir:
            cache_file = '%s/%s_%s_%s.json' % (cache_dir, self.network, resource, resourceid)
            try:  # looking into cache first
                j = json.load(open(cache_file), parse_float=str)
                return j
            except:
                pass

        try:
            url = self.get_url(resource, resourceid)
            r = requests.get(url, headers={'User-agent': 'Mozilla/5.0'})
            j = r.json(parse_float=str)
        except:
            raise RuntimeError('URL error: %s' % url)
        if cache_dir and cache_file:
            try:  # saving into cache
                json.dump(j, open(cache_file, 'w'))
            except:
                pass
        return j

    def get_tx(self, txhash):
        raise NotImplementedError


class TxApiInsight(TxApi):

    def __init__(self, network, url, zcash=None):
        super(TxApiInsight, self).__init__(network, url)
        self.zcash = zcash
        self.pushtx_url = url.replace('/api/', '/tx/send')

    def get_tx(self, txhash):

        data = self.fetch_json('tx', txhash)

        t = proto.TransactionType()
        t.version = data['version']
        t.lock_time = data['locktime']

        for vin in data['vin']:
            i = t._add_inputs()
            if 'coinbase' in vin.keys():
                i.prev_hash = b"\0" * 32
                i.prev_index = 0xffffffff  # signed int -1
                i.script_sig = binascii.unhexlify(vin['coinbase'])
                i.sequence = vin['sequence']

            else:
                i.prev_hash = binascii.unhexlify(vin['txid'])
                i.prev_index = vin['vout']
                i.script_sig = binascii.unhexlify(vin['scriptSig']['hex'])
                i.sequence = vin['sequence']

        for vout in data['vout']:
            o = t._add_bin_outputs()
            o.amount = int(Decimal(vout['value']) * 100000000)
            o.script_pubkey = binascii.unhexlify(vout['scriptPubKey']['hex'])

        if self.zcash:
            if t.version == 2:
                joinsplit_cnt = len(data['vjoinsplit'])
                if joinsplit_cnt == 0:
                    t.extra_data = b'\x00'
                else:
                    if joinsplit_cnt >= 253:
                        # we assume cnt < 253, so we can treat varIntLen(cnt) as 1
                        raise ValueError('Too many joinsplits')
                    extra_data_len = 1 + joinsplit_cnt * 1802 + 32 + 64
                    raw = self.fetch_json('rawtx', txhash)
                    raw = binascii.unhexlify(raw['rawtx'])
                    t.extra_data = raw[-extra_data_len:]

        return t


class TxApiSmartbit(TxApi):

    def get_tx(self, txhash):

        data = self.fetch_json('tx', txhash)

        data = data['transaction']

        t = proto.TransactionType()
        t.version = int(data['version'])
        t.lock_time = data['locktime']

        for vin in data['inputs']:
            i = t.inputs.add()
            if 'coinbase' in vin.keys():
                i.prev_hash = b"\0" * 32
                i.prev_index = 0xffffffff  # signed int -1
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


class TxApiBlockCypher(TxApi):

    def __init__(self, network, url, zcash=None):
        super(TxApiBlockCypher, self).__init__(network, url)
        self.pushtx_url = url.replace('//api.', '//live.').replace('/v1/', '/').replace('/main/', '/pushtx/')

    def get_tx(self, txhash):

        data = self.fetch_json('txs', txhash)

        t = proto.TransactionType()
        t.version = data['ver']
        t.lock_time = data.get('lock_time', 0)

        for vin in data['inputs']:
            i = t._add_inputs()
            if 'prev_hash' not in vin:
                i.prev_hash = b"\0" * 32
                i.prev_index = 0xffffffff  # signed int -1
                i.script_sig = binascii.unhexlify(vin['script'])
                i.sequence = vin['sequence']
            else:
                i.prev_hash = binascii.unhexlify(vin['prev_hash'])
                i.prev_index = vin['output_index']
                i.script_sig = binascii.unhexlify(vin['script'])
                i.sequence = vin['sequence']

        for vout in data['outputs']:
            o = t._add_bin_outputs()
            o.amount = int(str(vout['value']), 10)
            o.script_pubkey = binascii.unhexlify(vout['script'])

        return t


TxApiBitcoin = TxApiInsight(network='insight_bitcoin', url='https://btc-bitcore1.trezor.io/api/')
TxApiTestnet = TxApiInsight(network='insight_testnet', url='https://testnet-bitcore3.trezor.io/api/')
TxApiLitecoin = TxApiInsight(network='insight_litecoin', url='https://ltc-bitcore1.trezor.io/api/')
TxApiDash = TxApiInsight(network='insight_dash', url='https://dash-bitcore1.trezor.io/api/')
TxApiZcash = TxApiInsight(network='insight_zcash', url='https://zec-bitcore1.trezor.io/api/', zcash=True)
TxApiBcash = TxApiInsight(network='insight_bcash', url='https://bch-bitcore2.trezor.io/api/')
TxApiDecredTestnet = TxApiInsight(network='insight_decred_testnet', url='https://testnet.decred.org/api/')
TxApiDogecoin = TxApiBlockCypher(network='blockcypher_dogecoin', url='https://api.blockcypher.com/v1/doge/main/')
TxApiSegnet = TxApiSmartbit(network='smartbit_segnet', url='https://segnet-api.smartbit.com.au/v1/blockchain/')
TxApiMonacoin = TxApiInsight(network='insight_monacoin', url='https://mona.insight.monaco-ex.org/insight-api-monacoin/')
