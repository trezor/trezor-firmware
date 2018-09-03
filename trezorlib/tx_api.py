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
import json
from decimal import Decimal

import requests

from . import messages as proto

cache_dir = None


class TxApi(object):
    def __init__(self, network, url=None):
        self.network = network
        self.url = url

    def get_url(self, *args):
        return "/".join(map(str, [self.url, "api"] + list(args)))

    def fetch_json(self, resource, resourceid):
        global cache_dir
        if cache_dir:
            cache_file = "%s/%s_%s_%s.json" % (
                cache_dir,
                self.network,
                resource,
                resourceid,
            )
            try:  # looking into cache first
                j = json.load(open(cache_file), parse_float=str)
                return j
            except Exception:
                pass

        if not self.url:
            raise RuntimeError("No URL specified and tx not in cache")

        try:
            url = self.get_url(resource, resourceid)
            r = requests.get(url, headers={"User-agent": "Mozilla/5.0"})
            j = r.json(parse_float=str)
        except Exception:
            raise RuntimeError("URL error: %s" % url)
        if cache_dir and cache_file:
            try:  # saving into cache
                json.dump(j, open(cache_file, "w"))
            except Exception:
                pass
        return j

    def get_tx(self, txhash):
        raise NotImplementedError


class TxApiInsight(TxApi):
    def __init__(self, network, url=None, zcash=None, bip115=False):
        super().__init__(network, url)
        self.zcash = zcash
        self.bip115 = bip115
        if url:
            self.pushtx_url = self.url + "/tx/send"

    def get_block_hash(self, block_number):
        j = self.fetch_json("block-index", block_number)
        return binascii.unhexlify(j["blockHash"])

    def current_height(self):
        r = requests.get(self.get_url("status?q=getBlockCount"))
        j = r.json(parse_float=str)
        block_height = j["info"]["blocks"]
        return block_height

    def get_tx(self, txhash):

        data = self.fetch_json("tx", txhash)

        t = proto.TransactionType()
        t.version = data["version"]
        t.lock_time = data["locktime"]

        for vin in data["vin"]:
            i = t._add_inputs()
            if "coinbase" in vin.keys():
                i.prev_hash = b"\0" * 32
                i.prev_index = 0xffffffff  # signed int -1
                i.script_sig = binascii.unhexlify(vin["coinbase"])
                i.sequence = vin["sequence"]

            else:
                i.prev_hash = binascii.unhexlify(vin["txid"])
                i.prev_index = vin["vout"]
                i.script_sig = binascii.unhexlify(vin["scriptSig"]["hex"])
                i.sequence = vin["sequence"]

        for vout in data["vout"]:
            o = t._add_bin_outputs()
            o.amount = int(Decimal(vout["value"]) * 100000000)
            o.script_pubkey = binascii.unhexlify(vout["scriptPubKey"]["hex"])
            if self.bip115 and o.script_pubkey[-1] == 0xb4:
                # Verify if coin implements replay protection bip115 and script includes checkblockatheight opcode. 0xb4 - is op_code (OP_CHECKBLOCKATHEIGHT)
                # <OP_32> <32-byte block hash> <OP_3> <3-byte block height> <OP_CHECKBLOCKATHEIGHT>
                tail = o.script_pubkey[-38:]
                o.block_hash = tail[1:33]  # <32-byte block hash>
                o.block_height = int.from_bytes(
                    tail[34:37], byteorder="little"
                )  # <3-byte block height>

        if self.zcash:
            t.overwintered = data.get("fOverwintered", False)
            t.expiry = data.get("nExpiryHeight", False)
            if t.version >= 2:
                joinsplit_cnt = len(data["vjoinsplit"])
                if joinsplit_cnt == 0:
                    t.extra_data = b"\x00"
                else:
                    if joinsplit_cnt >= 253:
                        # we assume cnt < 253, so we can treat varIntLen(cnt) as 1
                        raise ValueError("Too many joinsplits")
                    extra_data_len = 1 + joinsplit_cnt * 1802 + 32 + 64
                    raw = self.fetch_json("rawtx", txhash)
                    raw = binascii.unhexlify(raw["rawtx"])
                    t.extra_data = raw[-extra_data_len:]

        return t
