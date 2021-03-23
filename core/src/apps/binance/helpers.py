from micropython import const

from trezor.crypto import bech32
from trezor.crypto.scripts import sha256_ripemd160_digest
from trezor.messages import (
    BinanceCancelMsg,
    BinanceInputOutput,
    BinanceOrderMsg,
    BinanceSignTx,
    BinanceTransferMsg,
)

ENVELOPE_BLUEPRINT = '{{"account_number":"{account_number}","chain_id":"{chain_id}","data":null,"memo":"{memo}","msgs":[{msgs}],"sequence":"{sequence}","source":"{source}"}}'
MSG_TRANSFER_BLUEPRINT = '{{"inputs":[{inputs}],"outputs":[{outputs}]}}'
MSG_NEWORDER_BLUEPRINT = '{{"id":"{id}","ordertype":{ordertype},"price":{price},"quantity":{quantity},"sender":"{sender}","side":{side},"symbol":"{symbol}","timeinforce":{timeinforce}}}'
MSG_CANCEL_BLUEPRINT = '{{"refid":"{refid}","sender":"{sender}","symbol":"{symbol}"}}'
INPUT_OUTPUT_BLUEPRINT = '{{"address":"{address}","coins":[{coins}]}}'
COIN_BLUEPRINT = '{{"amount":{amount},"denom":"{denom}"}}'

# 1*10^8 Jagers equal 1 BNB https://www.binance.vision/glossary/jager
DECIMALS = const(8)


def produce_json_for_signing(envelope: BinanceSignTx, msg) -> str:
    if BinanceTransferMsg.is_type_of(msg):
        json_msg = produce_transfer_json(msg)
    elif BinanceOrderMsg.is_type_of(msg):
        json_msg = produce_neworder_json(msg)
    elif BinanceCancelMsg.is_type_of(msg):
        json_msg = produce_cancel_json(msg)
    else:
        raise ValueError("input message unrecognized, is of type " + type(msg).__name__)

    if envelope.source is None or envelope.source < 0:
        raise ValueError("source missing or invalid")

    source = envelope.source

    return ENVELOPE_BLUEPRINT.format(
        account_number=envelope.account_number,
        chain_id=envelope.chain_id,
        memo=envelope.memo,
        msgs=json_msg,
        sequence=envelope.sequence,
        source=source,
    )


def produce_transfer_json(msg: BinanceTransferMsg) -> str:
    def make_input_output(input_output: BinanceInputOutput):
        coins = ",".join(
            COIN_BLUEPRINT.format(amount=c.amount, denom=c.denom)
            for c in input_output.coins
        )
        return INPUT_OUTPUT_BLUEPRINT.format(address=input_output.address, coins=coins)

    inputs = ",".join(make_input_output(i) for i in msg.inputs)
    outputs = ",".join(make_input_output(o) for o in msg.outputs)

    return MSG_TRANSFER_BLUEPRINT.format(inputs=inputs, outputs=outputs)


def produce_neworder_json(msg: BinanceOrderMsg) -> str:
    return MSG_NEWORDER_BLUEPRINT.format(
        id=msg.id,
        ordertype=msg.ordertype,
        price=msg.price,
        quantity=msg.quantity,
        sender=msg.sender,
        side=msg.side,
        symbol=msg.symbol,
        timeinforce=msg.timeinforce,
    )


def produce_cancel_json(msg: BinanceCancelMsg) -> str:
    return MSG_CANCEL_BLUEPRINT.format(
        refid=msg.refid, sender=msg.sender, symbol=msg.symbol
    )


def address_from_public_key(pubkey: bytes, hrp: str) -> str:
    """
    Address = RIPEMD160(SHA256(compressed public key))
    Address_Bech32 = HRP + '1' + bech32.encode(convert8BitsTo5Bits(RIPEMD160(SHA256(compressed public key))))
    HRP - bnb for productions, tbnb for tests
    """

    h = sha256_ripemd160_digest(pubkey)

    convertedbits = bech32.convertbits(h, 8, 5, False)

    return bech32.bech32_encode(hrp, convertedbits)
