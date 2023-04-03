from micropython import const
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezor.messages import BinanceInputOutput, BinanceSignTx
    from trezor.protobuf import MessageType

# 1*10^8 Jagers equal 1 BNB https://www.binance.vision/glossary/jager
DECIMALS = const(8)


# NOTE: it is 11 bytes smaller to define it on top level than inside a function
def _make_input_output(input_output: BinanceInputOutput) -> str:
    COIN_BLUEPRINT = '{{"amount":{},"denom":"{}"}}'
    INPUT_OUTPUT_BLUEPRINT = '{{"address":"{}","coins":[{}]}}'

    coins = ",".join(
        COIN_BLUEPRINT.format(c.amount, c.denom) for c in input_output.coins
    )
    return INPUT_OUTPUT_BLUEPRINT.format(input_output.address, coins)


def produce_json_for_signing(envelope: BinanceSignTx, msg: MessageType) -> str:
    from trezor import wire
    from trezor.messages import BinanceCancelMsg, BinanceOrderMsg, BinanceTransferMsg

    # NOTE: not defining kwargs in format string saves 7 bytes per each argument
    ENVELOPE_BLUEPRINT = '{{"account_number":"{}","chain_id":"{}","data":null,"memo":"{}","msgs":[{}],"sequence":"{}","source":"{}"}}'
    MSG_TRANSFER_BLUEPRINT = '{{"inputs":[{}],"outputs":[{}]}}'
    MSG_NEWORDER_BLUEPRINT = '{{"id":"{}","ordertype":{},"price":{},"quantity":{},"sender":"{}","side":{},"symbol":"{}","timeinforce":{}}}'
    MSG_CANCEL_BLUEPRINT = '{{"refid":"{}","sender":"{}","symbol":"{}"}}'

    if BinanceTransferMsg.is_type_of(msg):
        inputs = ",".join(_make_input_output(i) for i in msg.inputs)
        outputs = ",".join(_make_input_output(o) for o in msg.outputs)
        json_msg = MSG_TRANSFER_BLUEPRINT.format(inputs, outputs)
    elif BinanceOrderMsg.is_type_of(msg):
        json_msg = MSG_NEWORDER_BLUEPRINT.format(
            msg.id,
            msg.ordertype,
            msg.price,
            msg.quantity,
            msg.sender,
            msg.side,
            msg.symbol,
            msg.timeinforce,
        )
    elif BinanceCancelMsg.is_type_of(msg):
        json_msg = MSG_CANCEL_BLUEPRINT.format(msg.refid, msg.sender, msg.symbol)
    else:
        raise wire.ProcessError("input message unrecognized")

    if envelope.source < 0:
        raise wire.DataError("Source is invalid")

    return ENVELOPE_BLUEPRINT.format(
        envelope.account_number,
        envelope.chain_id,
        envelope.memo,
        json_msg,
        envelope.sequence,
        envelope.source,
    )


def address_from_public_key(pubkey: bytes, hrp: str) -> str:
    """
    Address = RIPEMD160(SHA256(compressed public key))
    Address_Bech32 = HRP + '1' + bech32.encode(convert8BitsTo5Bits(RIPEMD160(SHA256(compressed public key))))
    HRP - bnb for productions, tbnb for tests
    """
    from trezor.crypto import bech32
    from trezor.crypto.scripts import sha256_ripemd160

    h = sha256_ripemd160(pubkey).digest()

    assert (len(h) * 8) % 5 == 0  # no padding will be added by convertbits
    convertedbits = bech32.convertbits(h, 8, 5)
    return bech32.bech32_encode(hrp, convertedbits, bech32.Encoding.BECH32)
