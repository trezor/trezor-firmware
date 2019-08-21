# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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
import struct
from decimal import Decimal

import requests

from . import messages

cache_dir = None


def is_zcash(coin):
    lcn = coin["coin_name"].lower()
    return lcn.startswith("zcash") or lcn.startswith("komodo")


def is_capricoin(coin):
    return coin["coin_name"].lower().startswith("capricoin")


def is_dash(coin):
    return coin["coin_name"].lower().startswith("dash")


def pack_varint(n):
    if n < 253:
        return struct.pack("<B", n)
    elif n <= 0xFFFF:
        return struct.pack("<BH", 253, n)
    elif n <= 0xFFFFFFFF:
        return struct.pack("<BL", 254, n)
    else:
        return struct.pack("<BQ", 255, n)


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

    if is_dash(coin):
        dip2_type = data.get("type", 0)

        if t.version == 3 and dip2_type != 0:
            # It's a DIP2 special TX with payload

            if "extraPayloadSize" not in data or "extraPayload" not in data:
                raise ValueError("Payload data missing in DIP2 transaction")

            if data["extraPayloadSize"] * 2 != len(data["extraPayload"]):
                raise ValueError("length mismatch")
            t.extra_data = pack_varint(data["extraPayloadSize"]) + bytes.fromhex(
                data["extraPayload"]
            )

        # Trezor firmware doesn't understand the split of version and type, so let's mimic the
        # old serialization format
        t.version |= dip2_type << 16

    return t


class TxApi:
    def __init__(self, coin_data):
        self.coin_data = coin_data
        if coin_data["blockbook"]:
            self.url = random.choice(coin_data["blockbook"])
            self.pushtx_url = self.url + "/sendtx"
            self.type = "blockbook"
        elif coin_data["bitcore"]:
            self.url = random.choice(coin_data["bitcore"])
            self.pushtx_url = self.url + "/tx/send"
            self.type = "bitcore"
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
        method = "tx-specific" if self.type == "blockbook" else "tx"
        data = self.fetch_json(method, txhash)
        if is_zcash(self.coin_data) and data.get("vjoinsplit") and "hex" not in data:
            j = self.fetch_json("rawtx", txhash)
            data["hex"] = j["rawtx"]
        return data

    def get_tx(self, txhash):
        data = self.get_tx_data(txhash)
        return json_to_tx(self.coin_data, data)
