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

from typing import TYPE_CHECKING, List, Any, Union
import logging
from . import exceptions, messages
from .messages import ZcashSignatureType as SigType
from .tools import expect

if TYPE_CHECKING:
    from .client import TrezorClient
    from .protobuf import MessageType


LOG = logging.getLogger(__name__)


@expect(messages.ZcashViewingKey, field="key", ret_type=str)
def get_viewing_key(
    client: "TrezorClient",
    z_address_n: List[int],
    coin_name: str = "Zcash",
    full: bool = True
) -> "MessageType":
    """Returns Zcash Unified Full Viewing Key."""
    return client.call(
        messages.ZcashGetViewingKey(
            z_address_n=z_address_n,
            coin_name=coin_name,
            full=full,
        )
    )


@expect(messages.ZcashAddress, field="address", ret_type=str)
def get_address(
    client: "TrezorClient",
    t_address_n: Union[List[int], None] = None,
    z_address_n: Union[List[int], None] = None,
    diversifier_index: int = 0,
    show_display: bool = False,
    coin_name: str = "Zcash",
) -> "MessageType":
    """
    Returns a Zcash address.
    """
    return client.call(
        messages.ZcashGetAddress(
            t_address_n=t_address_n or [],
            z_address_n=z_address_n or [],
            diversifier_index=diversifier_index,
            show_display=show_display,
            coin_name=coin_name,
        )
    )


EMPTY_ANCHOR = bytes.fromhex("ae2935f1dfd8a24aed7c70df7de3a668eb7a49b1319880dde2bbd9031ae5d82f")


def sign_tx(
    client: "TrezorClient",
    inputs: List[Union[messages.TxInputType, messages.ZcashOrchardInput]],
    outputs: List[Union[messages.TxOutputType, messages.ZcashOrchardOutput]],
    coin_name: str = "Zcash",
    version_group_id: int = 0x26A7270A,  # protocol spec §7.1.2
    branch_id: int = 0xC2D6D0B4,  # https://zips.z.cash/zip-0252
    expiry: int = 0,
    z_address_n: Union[List[int], None] = None,
    anchor: Union[bytes, None] = None,
) -> Any:  # TODO: add the return type
    """
    Sign a Zcash transaction.
    Spending transparent and Orchard funds simultaneously is not supported.

    Parameters:
    -----------
    inputs: transaction inputs
    outputs: transaction outputs
    coin_name: coin name (currently "Zcash" or "Zcash Testnet")
    version_group_id: 0x26A7270A by default
    branch_id: 0xC2D6D0B4 by default
    expiry: 0 by default
    z_address_n: Orchard account ZIP-32 path
    anchor: Orchard anchor

    Example:
    --------
    protocol = zcash.sign_tx(
        inputs=[
            ZcashOrchardInput(...),
        ],
        outputs=[
            TxOutput(...),
            ZcashOrchardOutput(...),
        ]
        z_address_n=tools.parse_path("m/32h/133h/0h"),
        anchor=bytes.fromhex(...),
    )
    zcash_shielding_seed = next(protocol)
    ... # run Orchard prover in parallel here
    sighash = next(protocol)
    signatures, serialized_tx = next(protocol)
    """

    t_inputs = [x for x in inputs if type(x) in (messages.TxInput, messages.TxInputType)]
    t_outputs = [x for x in outputs if type(x) in (messages.TxOutput, messages.TxOutputType)]
    o_inputs = [x for x in inputs if isinstance(x, messages.ZcashOrchardInput)]
    o_outputs = [x for x in outputs if isinstance(x, messages.ZcashOrchardOutput)]

    if o_inputs and t_inputs:
        raise ValueError("Spending transparent and Orchard funds simultaneously is not supported.")
    if o_inputs or o_outputs:
        if z_address_n is None:
            raise ValueError("z_address_n argument is missing")
        if anchor is None:
            raise ValueError("anchor argument is missing")

    msg = messages.SignTx(
        inputs_count=len(t_inputs),
        outputs_count=len(t_outputs),
        coin_name=coin_name,
        version=5,
        version_group_id=version_group_id,
        branch_id=branch_id,
        expiry=expiry,
        orchard_params=messages.ZcashOrchardParams(
            inputs_count=len(o_inputs),
            outputs_count=len(o_outputs),
            anchor=anchor,
            address_n=z_address_n,
        ) if o_inputs or o_outputs else None,
    )

    if o_outputs or o_inputs:
        actions_count = max(len(o_outputs), len(o_inputs), 2)
    else:
        actions_count = 0

    serialized_tx = b""

    signatures = {
        SigType.TRANSPARENT: [None] * len(t_inputs),
        SigType.ORCHARD_SPEND_AUTH:  dict(),
    }

    LOG.info("T <- sign tx")
    res = client.call(msg)

    R = messages.RequestType
    while isinstance(res, messages.TxRequest):
        # If there's some part of signed transaction, let's add it
        if res.serialized:
            if res.serialized.serialized_tx:
                LOG.info("T -> serialized tx (%d bytes)", len(res.serialized.serialized_tx))
                serialized_tx += res.serialized.serialized_tx

            if res.serialized.signature_index is not None:
                idx = res.serialized.signature_index
                sig = res.serialized.signature
                sig_type = res.serialized.signature_type
                if sig_type == SigType.TRANSPARENT:
                    LOG.info("T -> t signature %d", idx)
                    if signatures[sig_type][idx] is not None:
                        raise ValueError("Transparent signature for index {0} already filled".format(idx))
                elif sig_type == SigType.ORCHARD_SPEND_AUTH:
                    LOG.info("T -> o signature %d", idx)
                    if signatures[sig_type].get(idx) is not None:
                        raise ValueError("Orchard signature for index {0} already filled".format(idx))
                    if idx >= actions_count:
                        raise IndexError("Orchard signature index out of range: {0}".format(idx))
                else:
                    raise ValueError("Unknown signature type: {0}.".format(sig_type))
                signatures[sig_type][idx] = sig

            if res.serialized.zcash_shielding_seed is not None:
                LOG.info("T -> shielding seed")
                yield res.serialized.zcash_shielding_seed

            if res.serialized.tx_sighash is not None:
                LOG.info("T -> sighash")
                yield res.serialized.tx_sighash

        LOG.info("")

        if res.request_type == R.TXFINISHED:
            break

        elif res.request_type == R.TXINPUT:
            LOG.info("T <- t input %d", res.details.request_index)
            msg = messages.TransactionType()
            msg.inputs = [t_inputs[res.details.request_index]]
            res = client.call(messages.TxAck(tx=msg))

        elif res.request_type == R.TXOUTPUT:
            LOG.info("T <- t output %d", res.details.request_index)
            msg = messages.TransactionType()
            msg.outputs = [t_outputs[res.details.request_index]]
            res = client.call(messages.TxAck(tx=msg))

        elif res.request_type == R.TXORCHARDINPUT:
            txi = o_inputs[res.details.request_index]
            LOG.info("T <- o input %d", res.details.request_index)
            res = client.call(txi)

        elif res.request_type == R.TXORCHARDOUTPUT:
            txo = o_outputs[res.details.request_index]
            LOG.info("T <- o output %d", res.details.request_index)
            res = client.call(txo)

        elif res.request_type == R.NO_OP:
            res = client.call(messages.ZcashAck())

        else:
            raise ValueError("unexpected request type: {0}".format(res.request_type))

    if not isinstance(res, messages.TxRequest):
        raise exceptions.TrezorException("Unexpected message")

    yield (signatures, serialized_tx)
