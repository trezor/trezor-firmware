# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import binascii
from decimal import Decimal
import requests
import json

from . import messages as proto
cache_dir = None


class TxApi(object):

    def __init__(self, network, url=None):
        self.network = network
        self.url = url

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

        if not self.url:
            raise RuntimeError("No URL specified and tx not in cache")

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

    def __init__(self, network, url=None, zcash=None):
        super().__init__(network, url)
        self.zcash = zcash
        if url:
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
            t.overwintered = data.get('fOverwintered', False)
            t.expiry = data.get('nExpiryHeight', False)
            if t.version >= 2:
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
