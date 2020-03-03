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

from decimal import Decimal


from . import messages


def _json_to_input(vin):
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

    return i


def _json_to_bin_output(vout):
    o = messages.TxOutputBinType()
    o.amount = int(Decimal(vout["value"]) * (10 ** 8))
    o.script_pubkey = bytes.fromhex(vout["scriptPubKey"]["hex"])
    return o


def json_to_tx(data):
    t = messages.TransactionType()
    t.version = data["version"]
    t.lock_time = data.get("locktime")
    t.inputs = [_json_to_input(vin) for vin in data["vin"]]
    t.bin_outputs = [_json_to_bin_output(vout) for vout in data["vout"]]
    return t
