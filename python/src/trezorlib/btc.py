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

from . import exceptions, messages
from .tools import expect, normalize_nfc, session


def from_json(json_dict):
    def make_input(vin):
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

    def make_bin_output(vout):
        o = messages.TxOutputBinType()
        o.amount = int(Decimal(vout["value"]) * (10 ** 8))
        o.script_pubkey = bytes.fromhex(vout["scriptPubKey"]["hex"])
        return o

    t = messages.TransactionType()
    t.version = json_dict["version"]
    t.lock_time = json_dict.get("locktime")
    t.inputs = [make_input(vin) for vin in json_dict["vin"]]
    t.bin_outputs = [make_bin_output(vout) for vout in json_dict["vout"]]
    return t


@expect(messages.PublicKey)
def get_public_node(
    client,
    n,
    ecdsa_curve_name=None,
    show_display=False,
    coin_name=None,
    script_type=messages.InputScriptType.SPENDADDRESS,
):
    return client.call(
        messages.GetPublicKey(
            address_n=n,
            ecdsa_curve_name=ecdsa_curve_name,
            show_display=show_display,
            coin_name=coin_name,
            script_type=script_type,
        )
    )


@expect(messages.Address, field="address")
def get_address(
    client,
    coin_name,
    n,
    show_display=False,
    multisig=None,
    script_type=messages.InputScriptType.SPENDADDRESS,
):
    return client.call(
        messages.GetAddress(
            address_n=n,
            coin_name=coin_name,
            show_display=show_display,
            multisig=multisig,
            script_type=script_type,
        )
    )


@expect(messages.OwnershipId, field="ownership_id")
def get_ownership_id(
    client,
    coin_name,
    n,
    multisig=None,
    script_type=messages.InputScriptType.SPENDADDRESS,
):
    return client.call(
        messages.GetOwnershipId(
            address_n=n,
            coin_name=coin_name,
            multisig=multisig,
            script_type=script_type,
        )
    )


def get_ownership_proof(
    client,
    coin_name,
    n,
    multisig=None,
    script_type=messages.InputScriptType.SPENDADDRESS,
    user_confirmation=False,
    ownership_ids=None,
    commitment_data=None,
    preauthorized=False,
):
    if preauthorized:
        res = client.call(messages.DoPreauthorized())
        if not isinstance(res, messages.PreauthorizedRequest):
            raise exceptions.TrezorException("Unexpected message")

    res = client.call(
        messages.GetOwnershipProof(
            address_n=n,
            coin_name=coin_name,
            script_type=script_type,
            multisig=multisig,
            user_confirmation=user_confirmation,
            ownership_ids=ownership_ids,
            commitment_data=commitment_data,
        )
    )

    if not isinstance(res, messages.OwnershipProof):
        raise exceptions.TrezorException("Unexpected message")

    return res.ownership_proof, res.signature


@expect(messages.MessageSignature)
def sign_message(
    client, coin_name, n, message, script_type=messages.InputScriptType.SPENDADDRESS
):
    message = normalize_nfc(message)
    return client.call(
        messages.SignMessage(
            coin_name=coin_name, address_n=n, message=message, script_type=script_type
        )
    )


def verify_message(client, coin_name, address, signature, message):
    message = normalize_nfc(message)
    try:
        resp = client.call(
            messages.VerifyMessage(
                address=address,
                signature=signature,
                message=message,
                coin_name=coin_name,
            )
        )
    except exceptions.TrezorFailure:
        return False
    return isinstance(resp, messages.Success)


@session
def sign_tx(
    client,
    coin_name,
    inputs,
    outputs,
    details=None,
    prev_txes=None,
    preauthorized=False,
):
    this_tx = messages.TransactionType(inputs=inputs, outputs=outputs)

    if details is None:
        signtx = messages.SignTx()
    else:
        signtx = details

    signtx.coin_name = coin_name
    signtx.inputs_count = len(inputs)
    signtx.outputs_count = len(outputs)

    if preauthorized:
        res = client.call(messages.DoPreauthorized())
        if not isinstance(res, messages.PreauthorizedRequest):
            raise exceptions.TrezorException("Unexpected message")

    res = client.call(signtx)

    # Prepare structure for signatures
    signatures = [None] * len(inputs)
    serialized_tx = b""

    def copy_tx_meta(tx):
        tx_copy = messages.TransactionType(**tx)
        # clear fields
        tx_copy.inputs_cnt = len(tx.inputs)
        tx_copy.inputs = []
        tx_copy.outputs_cnt = len(tx.bin_outputs or tx.outputs)
        tx_copy.outputs = []
        tx_copy.bin_outputs = []
        tx_copy.extra_data_len = len(tx.extra_data or b"")
        tx_copy.extra_data = None
        return tx_copy

    R = messages.RequestType
    while isinstance(res, messages.TxRequest):
        # If there's some part of signed transaction, let's add it
        if res.serialized:
            if res.serialized.serialized_tx:
                serialized_tx += res.serialized.serialized_tx

            if res.serialized.signature_index is not None:
                idx = res.serialized.signature_index
                sig = res.serialized.signature
                if signatures[idx] is not None:
                    raise ValueError("Signature for index %d already filled" % idx)
                signatures[idx] = sig

        if res.request_type == R.TXFINISHED:
            break

        # Device asked for one more information, let's process it.
        if res.details.tx_hash is not None:
            current_tx = prev_txes[res.details.tx_hash]
        else:
            current_tx = this_tx

        if res.request_type == R.TXMETA:
            msg = copy_tx_meta(current_tx)
            res = client.call(messages.TxAck(tx=msg))

        elif res.request_type == R.TXINPUT:
            msg = messages.TransactionType()
            msg.inputs = [current_tx.inputs[res.details.request_index]]
            res = client.call(messages.TxAck(tx=msg))

        elif res.request_type == R.TXOUTPUT:
            msg = messages.TransactionType()
            if res.details.tx_hash:
                msg.bin_outputs = [current_tx.bin_outputs[res.details.request_index]]
            else:
                msg.outputs = [current_tx.outputs[res.details.request_index]]

            res = client.call(messages.TxAck(tx=msg))

        elif res.request_type == R.TXEXTRADATA:
            o, l = res.details.extra_data_offset, res.details.extra_data_len
            msg = messages.TransactionType()
            msg.extra_data = current_tx.extra_data[o : o + l]
            res = client.call(messages.TxAck(tx=msg))

    if not isinstance(res, messages.TxRequest):
        raise exceptions.TrezorException("Unexpected message")

    for i, sig in zip(inputs, signatures):
        if i.script_type != messages.InputScriptType.EXTERNAL and sig is None:
            raise exceptions.TrezorException("Some signatures are missing!")

    return signatures, serialized_tx


@expect(messages.Success, field="message")
def authorize_coinjoin(
    client,
    coordinator,
    max_total_fee,
    n,
    coin_name,
    fee_per_anonymity=None,
    script_type=messages.InputScriptType.SPENDADDRESS,
):
    return client.call(
        messages.AuthorizeCoinJoin(
            coordinator=coordinator,
            max_total_fee=max_total_fee,
            address_n=n,
            coin_name=coin_name,
            fee_per_anonymity=fee_per_anonymity,
            script_type=script_type,
        )
    )
