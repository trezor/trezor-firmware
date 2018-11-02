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

import random
from decimal import Decimal

import requests

from . import messages

cache_dir = None


def is_zcash(coin):
    return coin["coin_name"].lower().startswith("zcash")


def is_capricoin(coin):
    return coin["coin_name"].lower().startswith("capricoin")


def _json_to_input(coin, vin):
    i = messages.TxInputType()
    if "coinbase" in vin:
        i.prev_hash = b"\0" * 32
        i.prev_index = 0xFFFFFFFF  # signed int -1
        i.script_sig = bytes.fromhex(vin["coinbase"])
        i.sequence = vin["sequence"]

    else:
        i.prev_hash = bytes.fromhex(vin["txid"])
        i.prev_index = vin["vout"]
        i.script_sig = bytes.fromhex(vin["scriptSig"]["hex"])
        i.sequence = vin["sequence"]

    if coin["decred"]:
        i.decred_tree = vin["tree"]
        # TODO: support amountIn, blockHeight, blockIndex

    return i


def _json_to_bin_output(coin, vout):
    o = messages.TxOutputBinType()
    o.amount = int(Decimal(vout["value"]) * 100000000)
    o.script_pubkey = bytes.fromhex(vout["scriptPubKey"]["hex"])
    if coin["bip115"] and o.script_pubkey[-1] == 0xB4:
        # Verify if coin implements replay protection bip115 and script includes
        # checkblockatheight opcode. 0xb4 - is op_code (OP_CHECKBLOCKATHEIGHT)
        # <OP_32> <32-byte block hash> <OP_3> <3-byte block height> <OP_CHECKBLOCKATHEIGHT>
        tail = o.script_pubkey[-38:]
        o.block_hash = tail[1:33]  # <32-byte block hash>
        o.block_height = int.from_bytes(tail[34:37], "little")  # <3-byte block height>
    if coin["decred"]:
        o.decred_script_version = vout["version"]

    return o


def json_to_tx(coin, data):
    t = messages.TransactionType()
    t.version = data["version"]
    t.lock_time = data.get("locktime")

    if is_capricoin(coin):
        t.timestamp = data["time"]

    if coin["decred"]:
        t.expiry = data["expiry"]

    if is_zcash(coin):
        t.overwintered = data.get("fOverwintered", False)
        t.expiry = data.get("nExpiryHeight", None)
        t.version_group_id = data.get("nVersionGroupId", None)

    t.inputs = [_json_to_input(coin, vin) for vin in data["vin"]]
    t.bin_outputs = [_json_to_bin_output(coin, vout) for vout in data["vout"]]

    # zcash extra data
    if is_zcash(coin) and t.version >= 2:
        joinsplit_cnt = len(data["vjoinsplit"])
        if joinsplit_cnt == 0:
            t.extra_data = b"\x00"
        elif joinsplit_cnt >= 253:
            # we assume cnt < 253, so we can treat varIntLen(cnt) as 1
            raise ValueError("Too many joinsplits")
        elif "hex" not in data:
            raise ValueError("Raw TX data required for Zcash joinsplit transaction")
        else:
            rawtx = bytes.fromhex(data["hex"])
            extra_data_len = 1 + joinsplit_cnt * 1802 + 32 + 64
            t.extra_data = rawtx[-extra_data_len:]

    return t


class TxApi:
    def __init__(self, coin_data):
        self.coin_data = coin_data
        if coin_data["blockbook"]:
            self.url = random.choice(coin_data["blockbook"])
            self.pushtx_url = self.url + "/sendtx"
        elif coin_data["bitcore"]:
            self.url = random.choice(coin_data["bitcore"])
            self.pushtx_url = self.url + "/tx/send"
        else:
            raise ValueError("No API URL in coin data")

    def fetch_json(self, *path, **params):
        url = self.url + "/api/" + "/".join(map(str, path))
        return requests.get(url, params=params).json(parse_float=Decimal)

    def get_block_hash(self, block_number):
        j = self.fetch_json("block-index", block_number)
        return bytes.fromhex(j["blockHash"])

    def current_height(self):
        j = self.fetch_json("status", q="getBlockCount")
        return j["info"]["blocks"]

    def __getitem__(self, txhash):
        return self.get_tx(txhash.hex())

    def get_tx_data(self, txhash):
        data = self.fetch_json("tx", txhash)
        if is_zcash(self.coin_data) and data.get("vjoinsplit") and "hex" not in data:
            j = self.fetch_json("rawtx", txhash)
            data["hex"] = j["rawtx"]
        return data

    def get_tx(self, txhash):
        data = self.get_tx_data(txhash)
        return json_to_tx(self.coin_data, data)
