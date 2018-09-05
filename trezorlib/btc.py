from . import messages as proto
from .tools import CallException, expect, normalize_nfc, session


@expect(proto.PublicKey)
def get_public_node(
    client,
    n,
    ecdsa_curve_name=None,
    show_display=False,
    coin_name=None,
    script_type=proto.InputScriptType.SPENDADDRESS,
):
    return client.call(
        proto.GetPublicKey(
            address_n=n,
            ecdsa_curve_name=ecdsa_curve_name,
            show_display=show_display,
            coin_name=coin_name,
            script_type=script_type,
        )
    )


@expect(proto.Address, field="address")
def get_address(
    client,
    coin_name,
    n,
    show_display=False,
    multisig=None,
    script_type=proto.InputScriptType.SPENDADDRESS,
):
    if multisig:
        return client.call(
            proto.GetAddress(
                address_n=n,
                coin_name=coin_name,
                show_display=show_display,
                multisig=multisig,
                script_type=script_type,
            )
        )
    else:
        return client.call(
            proto.GetAddress(
                address_n=n,
                coin_name=coin_name,
                show_display=show_display,
                script_type=script_type,
            )
        )


@expect(proto.MessageSignature)
def sign_message(
    client, coin_name, n, message, script_type=proto.InputScriptType.SPENDADDRESS
):
    message = normalize_nfc(message)
    return client.call(
        proto.SignMessage(
            coin_name=coin_name, address_n=n, message=message, script_type=script_type
        )
    )


def verify_message(client, coin_name, address, signature, message):
    message = normalize_nfc(message)
    try:
        resp = client.call(
            proto.VerifyMessage(
                address=address,
                signature=signature,
                message=message,
                coin_name=coin_name,
            )
        )
    except CallException as e:
        resp = e
    return isinstance(resp, proto.Success)


@session
def sign_tx(
    client,
    coin_name,
    inputs,
    outputs,
    version=None,
    lock_time=None,
    expiry=None,
    overwintered=None,
    debug_processor=None,
):
    # start = time.time()
    txes = client._prepare_sign_tx(inputs, outputs)

    # Prepare and send initial message
    tx = proto.SignTx()
    tx.inputs_count = len(inputs)
    tx.outputs_count = len(outputs)
    tx.coin_name = coin_name
    if version is not None:
        tx.version = version
    if lock_time is not None:
        tx.lock_time = lock_time
    if expiry is not None:
        tx.expiry = expiry
    if overwintered is not None:
        tx.overwintered = overwintered
    res = client.call(tx)

    # Prepare structure for signatures
    signatures = [None] * len(inputs)
    serialized_tx = b""

    counter = 0
    while True:
        counter += 1

        if isinstance(res, proto.Failure):
            raise CallException("Signing failed")

        if not isinstance(res, proto.TxRequest):
            raise CallException("Unexpected message")

        # If there's some part of signed transaction, let's add it
        if res.serialized and res.serialized.serialized_tx:
            # log("RECEIVED PART OF SERIALIZED TX (%d BYTES)" % len(res.serialized.serialized_tx))
            serialized_tx += res.serialized.serialized_tx

        if res.serialized and res.serialized.signature_index is not None:
            if signatures[res.serialized.signature_index] is not None:
                raise ValueError(
                    "Signature for index %d already filled"
                    % res.serialized.signature_index
                )
            signatures[res.serialized.signature_index] = res.serialized.signature

        if res.request_type == proto.RequestType.TXFINISHED:
            # Device didn't ask for more information, finish workflow
            break

        # Device asked for one more information, let's process it.
        if not res.details.tx_hash:
            current_tx = txes[None]
        else:
            current_tx = txes[bytes(res.details.tx_hash)]

        if res.request_type == proto.RequestType.TXMETA:
            msg = proto.TransactionType()
            msg.version = current_tx.version
            msg.lock_time = current_tx.lock_time
            msg.inputs_cnt = len(current_tx.inputs)
            if res.details.tx_hash:
                msg.outputs_cnt = len(current_tx.bin_outputs)
            else:
                msg.outputs_cnt = len(current_tx.outputs)
            msg.extra_data_len = (
                len(current_tx.extra_data) if current_tx.extra_data else 0
            )
            res = client.call(proto.TxAck(tx=msg))
            continue

        elif res.request_type == proto.RequestType.TXINPUT:
            msg = proto.TransactionType()
            msg.inputs = [current_tx.inputs[res.details.request_index]]
            if debug_processor is not None:
                # msg needs to be deep copied so when it's modified
                # the other messages stay intact
                from copy import deepcopy

                msg = deepcopy(msg)
                # If debug_processor function is provided,
                # pass thru it the request and prepared response.
                # This is useful for tests, see test_msg_signtx
                msg = debug_processor(res, msg)

            res = client.call(proto.TxAck(tx=msg))
            continue

        elif res.request_type == proto.RequestType.TXOUTPUT:
            msg = proto.TransactionType()
            if res.details.tx_hash:
                msg.bin_outputs = [current_tx.bin_outputs[res.details.request_index]]
            else:
                msg.outputs = [current_tx.outputs[res.details.request_index]]

            if debug_processor is not None:
                # msg needs to be deep copied so when it's modified
                # the other messages stay intact
                from copy import deepcopy

                msg = deepcopy(msg)
                # If debug_processor function is provided,
                # pass thru it the request and prepared response.
                # This is useful for tests, see test_msg_signtx
                msg = debug_processor(res, msg)

            res = client.call(proto.TxAck(tx=msg))
            continue

        elif res.request_type == proto.RequestType.TXEXTRADATA:
            o, l = res.details.extra_data_offset, res.details.extra_data_len
            msg = proto.TransactionType()
            msg.extra_data = current_tx.extra_data[o : o + l]
            res = client.call(proto.TxAck(tx=msg))
            continue

    if None in signatures:
        raise RuntimeError("Some signatures are missing!")

    # log("SIGNED IN %.03f SECONDS, CALLED %d MESSAGES, %d BYTES" %
    #    (time.time() - start, counter, len(serialized_tx)))

    return (signatures, serialized_tx)
