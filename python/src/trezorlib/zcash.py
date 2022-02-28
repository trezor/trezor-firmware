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

from . import exceptions, messages
from .tools import expect

@expect(messages.DebugZcashDiagResponse, field="data")
def diag(client, ins=b"", data=b""):
    """Dangerous temporary function for diagnostic purposes."""
    return client.call(
        messages.DebugZcashDiagRequest(ins=ins, data=data)
    )

@expect(messages.ZcashFullViewingKey, field="fvk")
def get_fvk(client, z_address_n, coin_name="Zcash",):
    """Returns raw Zcash Orchard Full Viewing Key encoded as:

    ak (32 bytes) || nk (32 bytes) || rivk (32 bytes)
    
    acording to the https://zips.z.cash/protocol/protocol.pdf § 5.6.4.4"""
    return client.call(
        messages.ZcashGetFullViewingKey(
            z_address_n=z_address_n,
            coin_name=coin_name,
        )
    )

@expect(messages.ZcashIncomingViewingKey, field="ivk")
def get_ivk(client, z_address_n, coin_name = "Zcash",):
    """Returns raw Zcash Orchard Incoming Viewing Key encoded as:

    dk (32 bytes) || ivk (32 bytes)
    
    acording to the https://zips.z.cash/protocol/protocol.pdf § 5.6.4.3"""
    return client.call(
        messages.ZcashGetIncomingViewingKey(
            z_address_n=z_address_n,
            coin_name=coin_name,
        )
    )

@expect(messages.ZcashAddress, field="address")
def get_address(
    client,
    t_address_n=[],
    z_address_n=[],
    diversifier_index=0,
    show_display=False,
    coin_name = "Zcash",
):
    """Returns Zcash address."""
    return client.call(
        messages.ZcashGetAddress(
            t_address_n=t_address_n,
            z_address_n=z_address_n,
            diversifier_index=diversifier_index,
            show_display=show_display,
            coin_name=coin_name,
        )
    )

def sign_tx(
    client,
    o_inputs = [],
    o_outputs = [],
    t_inputs = [],
    t_outputs = [],
    coin_name = "Zcash",
):
    msg = messages.SignTx()

    msg.inputs_count = len(t_inputs)
    msg.outputs_count = len(t_outputs)
    msg.coin_name = coin_name
    msg.version = 5                              
    msg.version_group_id = 0x892F2085 # protocol spec §7.1.2           
    msg.branch_id = 0x37519621 # https://zips.z.cash/zip-0252
    msg.expiry = 0

    orchard = messages.ZcashOrchardBundleInfo()
    orchard.outputs_count = len(o_outputs)
    orchard.inputs_count = len(o_inputs)
    orchard.anchor = 32*b"\x00"
    orchard.enable_spends = True
    orchard.enable_outputs = True

    msg.orchard = orchard

    res = client.call(msg)
    # Prepare structure for signatures
    t_signatures = [None] * len(t_inputs)  # transparent
    o_signatures = [None] * len(o_inputs)    # Orchard

    orchard_input_hmacs = [None] * len(o_inputs)
    orchard_output_hmacs = [None] * len(o_outputs)

    serialized_tx = b""
    seed = None

    R = messages.RequestType
    while isinstance(res, messages.TxRequest):
        # If there's some part of signed transaction, let's add it
        if res.serialized:
            if res.serialized.serialized_tx:
                serialized_tx += res.serialized.serialized_tx

            if res.serialized.signature_index is not None:
                idx = res.serialized.signature_index
                sig = res.serialized.signature
                print("set  t signature", idx)
                if t_signatures[idx] is not None:
                    raise ValueError("Signature for index %d already filled" % idx)
                t_signatures[idx] = sig

            if res.serialized.orchard or True:
                o = res.serialized.orchard
                if o.signature_index is not None:
                    idx = o.signature_index
                    sig = o.signature
                    print("set  o signature", idx)
                    if o_signatures[idx] is not None:
                        raise ValueError("Signature for index %d already filled" % idx)
                    o_signatures[idx] = sig

                if o.randomness_seed is not None:
                    print("set  o seed")
                    seed = o.randomness_seed

                if o.hmac_index is not None:
                    if o.hmac_type is messages.ZcashHMACType.ORCHARD_INPUT:
                        hmacs = orchard_input_hmacs
                        print(f"hmac o input  {o.hmac_index}")
                    if o.hmac_type is messages.ZcashHMACType.ORCHARD_OUTPUT:
                        hmacs = orchard_output_hmacs
                        print(f"hmac o output {o.hmac_index}")

                    assert hmacs[o.hmac_index] is None
                    hmacs[o.hmac_index] = o.hmac

        if res.request_type == R.TXFINISHED:
            break

        elif res.request_type == R.TXORCHARDINPUT:
            txi = o_inputs[res.details.request_index]
            msg = messages.ZcashOrchardInput(
                internal = True,  # TODO
                amount = txi.get("amount") or 0,
                note = txi["note"],
                hmac = orchard_input_hmacs[res.details.request_index],
            )
            print("send o input ", res.details.request_index)
            res = client.call(msg)

        elif res.request_type == R.TXORCHARDOUTPUT:
            output = o_outputs[res.details.request_index]
            msg = messages.ZcashOrchardOutput(
                address = output.get("address"),
                amount = output["amount"],
                memo = output.get("memo"),
                hmac = orchard_output_hmacs[res.details.request_index],
            )
            print("send o output", res.details.request_index)
            res = client.call(msg)

        elif res.request_type == R.TXINPUT:
            print("send t input", res.details.request_index)
            msg = messages.TransactionType()
            msg.inputs = [t_inputs[res.details.request_index]]
            res = client.call(messages.TxAck(tx=msg))

        elif res.request_type == R.TXOUTPUT:
            print("send t output", res.details.request_index)
            msg = messages.TransactionType()
            msg.outputs = [t_outputs[res.details.request_index]]
            res = client.call(messages.TxAck(tx=msg))

        else:
            raise ValueError("unexpected request type: {}".format(res.request_type))


    if not isinstance(res, messages.TxRequest):
        raise exceptions.TrezorException("Unexpected message")

    #for i, sig in zip(inputs, signatures):
    #    if i.script_type != messages.InputScriptType.EXTERNAL and sig is None:
    #        raise exceptions.TrezorException("Some signatures are missing!")

    return t_signatures, o_signatures, serialized_tx, seed