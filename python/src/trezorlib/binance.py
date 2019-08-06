from . import messages
from .protobuf import dict_to_proto
from .tools import expect, session


@expect(messages.BinanceAddress, field="address")
def get_address(client, address_n, show_display=False):
    return client.call(
        messages.BinanceGetAddress(address_n=address_n, show_display=show_display)
    )


@expect(messages.BinancePublicKey, field="public_key")
def get_public_key(client, address_n, show_display=False):
    return client.call(
        messages.BinanceGetPublicKey(address_n=address_n, show_display=show_display)
    )


@session
def sign_tx(client, address_n, tx_json):
    msg = tx_json["msgs"][0]
    envelope = dict_to_proto(messages.BinanceSignTx, tx_json)
    envelope.msg_count = 1
    envelope.address_n = address_n

    response = client.call(envelope)

    if not isinstance(response, messages.BinanceTxRequest):
        raise RuntimeError(
            "Invalid response, expected BinanceTxRequest, received "
            + type(response).__name__
        )

    if "refid" in msg:
        msg = dict_to_proto(messages.BinanceCancelMsg, msg)
    elif "inputs" in msg:
        msg = dict_to_proto(messages.BinanceTransferMsg, msg)
    elif "ordertype" in msg:
        msg = dict_to_proto(messages.BinanceOrderMsg, msg)
    else:
        raise ValueError("can not determine msg type")

    response = client.call(msg)

    if not isinstance(response, messages.BinanceSignedTx):
        raise RuntimeError(
            "Invalid response, expected BinanceSignedTx, received "
            + type(response).__name__
        )

    return response
