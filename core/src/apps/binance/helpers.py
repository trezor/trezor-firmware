from micropython import const

from trezor.crypto import bech32
from trezor.crypto.hashlib import ripemd160, sha256
from trezor.messages.BinanceInputOutput import BinanceInputOutput
from trezor.messages.BinanceCoin import BinanceCoin
from trezor.messages.BinanceTransferMsg import BinanceTransferMsg
from trezor.messages.BinanceOrderMsg import BinanceOrderMsg
from trezor.messages.BinanceCancelMsg import BinanceCancelMsg
from trezor.messages.BinanceSignTx import BinanceSignTx

from apps.common import HARDENED


_ENVELOPE_BLUEPRINT = '{{"account_number":"{account_number}","chain_id":"{chain_id}","memo":"{memo}","msgs":[{msgs}],"sequence":"{sequence}"}}'
_MSG_TRANSFER_BLUEPRINT = '{{"inputs":[{{"address":"{input_address}","coins":[{{"amount":{input_amount},"denom":"{input_denom}"}}]}}],"outputs":[{{"address":"{output_address}","coins":[{{"amount":{output_amount},"denom":"{output_denom}"}}]}}]}}'
_MSG_NEWORDER_BLUEPRINT = '{{"id":"{id}","ordertype":{ordertype},"price":{price},"quantity":{quantity},"sender":"{sender}","side":{side},"symbol":"{symbol}","timeinforce":{timeinforce}}}'
_MSG_CANCEL_BLUEPRINT = '{{"refid":"{refid}","sender":"{sender}","symbol":"{symbol}}}'


def produce_json_for_signing(envelope: BinanceSignTx, msg) -> str:
    if isinstance(msg, BinanceTransferMsg):
        jsonmsg = produce_transfer_json(msg)
    elif isinstance(msg, BinanceOrderMsg):
        jsonmsg = produce_neworder_json(msg)
    elif isinstance(msg, BinanceCancelMsg):
        jsonmsg = produce_cancel_json(msg)
    else:
        raise ValueError('input message unrecognized, is of type '+type(msg).__name__)

    return _ENVELOPE_BLUEPRINT.format(account_number=envelope.account_number, chain_id=envelope.chain_id, memo=envelope.memo, msgs=jsonmsg, sequence=envelope.sequence)

def produce_transfer_json(msg: BinanceTransferMsg) -> str:
    firstinput = next(iter(msg.inputs.coins))
    firstoutput = next(iter(msg.outputs.coins))

    return _MSG_TRANSFER_BLUEPRINT.format(input_address=msg.inputs.address, input_amount=firstinput.amount, input_denom=firstinput.denom,
                                          output_address=msg.outputs.address, output_amount=firstoutput.amount, output_denom=firstoutput.denom)


def produce_neworder_json(msg: BinanceOrderMsg) -> str:
    return _MSG_NEWORDER_BLUEPRINT.format(id=msg.id, ordertype=msg.ordertype, price=msg.price, quantity=msg.quantity, 
                                          sender=msg.sender, side=msg.side, symbol=msg.symbol, timeinforce=msg.timeinforce)


def produce_cancel_json(msg: BinanceCancelMsg) -> str:
    return _MSG_CANCEL_BLUEPRINT.format(refid=msg.refid, sender=msg.sender, symbol=msg.symbol)


def address_from_public_key(pubkey: bytes) -> str:
    # Address = RIPEMD160(SHA256(compressed public key))
    # Address_Bech32 = HRP + '1' + bech32.encode(convert8BitsTo5Bits(RIPEMD160(SHA256(compressed public key))))
    # HRP - bnb for productions, tbnb for tests

    h = sha256(pubkey).digest()
    h = ripemd160(h).digest()

    convertedbits = bech32.convertbits(h, 8, 5, False)

    # TODO: handle testnet vs mainnet
    return bech32.bech32_encode("tbnb", convertedbits)

def validate_full_path(path: list) -> bool:
    """
    Validates derivation path to equal 44'/714'/a'/0/0,
    where `a` is an account index from 0 to 1 000 000.
    Similar to Ethereum this should be 44'/714'/a', but for
    compatibility with other HW vendors we use 44'/714'/a'/0/0.
    """
    if len(path) != 5:
        return False
    if path[0] != 44 | HARDENED:
        return False
    if path[1] != 714 | HARDENED:
        return False
    if path[2] < HARDENED or path[2] > 1000000 | HARDENED:
        return False
    if path[3] != 0:
        return False
    if path[4] != 0:
        return False
    return True