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

from . import messages
from .tools import CallException, expect, normalize_nfc, session


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
    except CallException as e:
        resp = e
    return isinstance(resp, messages.Success)


@session
def sign_tx(client, coin_name, inputs, outputs, details=None, prev_txes=None):
    # set up a transactions dict
    txes = {None: messages.TransactionType(inputs=inputs, outputs=outputs)}
    # preload all relevant transactions ahead of time
    for inp in inputs:
        if inp.script_type not in (
            messages.InputScriptType.SPENDP2SHWITNESS,
            messages.InputScriptType.SPENDWITNESS,
            messages.InputScriptType.EXTERNAL,
        ):
            try:
                prev_tx = prev_txes[inp.prev_hash]
            except Exception as e:
                raise ValueError("Could not retrieve prev_tx") from e
            if not isinstance(prev_tx, messages.TransactionType):
                raise ValueError("Invalid value for prev_tx") from None
            txes[inp.prev_hash] = prev_tx

    if details is None:
        signtx = messages.SignTx()
    else:
        signtx = details

    signtx.coin_name = coin_name
    signtx.inputs_count = len(inputs)
    signtx.outputs_count = len(outputs)

    res = client.call(signtx)

    # Prepare structure for signatures
    signatures = [None] * len(inputs)
    serialized_tx = b""

    def copy_tx_meta(tx):
        tx_copy = messages.TransactionType()
        tx_copy.CopyFrom(tx)
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
        current_tx = txes[res.details.tx_hash]

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

    if isinstance(res, messages.Failure):
        raise CallException("Signing failed")

    if not isinstance(res, messages.TxRequest):
        raise CallException("Unexpected message")

    if None in signatures:
        raise RuntimeError("Some signatures are missing!")

    return signatures, serialized_tx
