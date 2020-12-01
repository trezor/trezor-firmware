from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.messages.InputScriptType import SPENDADDRESS, SPENDP2SHWITNESS, SPENDWITNESS
from trezor.messages.Success import Success

from apps.common import coins
from apps.common.signverify import message_digest, require_confirm_verify_message

from .addresses import (
    address_p2wpkh,
    address_p2wpkh_in_p2sh,
    address_pkh,
    address_short,
    address_to_cashaddr,
)

if False:
    from trezor.messages.VerifyMessage import VerifyMessage
    from trezor.messages.TxInputType import EnumTypeInputScriptType


async def verify_message(ctx: wire.Context, msg: VerifyMessage) -> Success:
    message = msg.message
    address = msg.address
    signature = msg.signature
    coin_name = msg.coin_name or "Bitcoin"
    coin = coins.by_name(coin_name)

    digest = message_digest(coin, message)

    recid = signature[0]
    if recid >= 27 and recid <= 34:
        # p2pkh
        script_type: EnumTypeInputScriptType = SPENDADDRESS
    elif recid >= 35 and recid <= 38:
        # segwit-in-p2sh
        script_type = SPENDP2SHWITNESS
        signature = bytes([signature[0] - 4]) + signature[1:]
    elif recid >= 39 and recid <= 42:
        # native segwit
        script_type = SPENDWITNESS
        signature = bytes([signature[0] - 8]) + signature[1:]
    else:
        raise wire.ProcessError("Invalid signature")

    pubkey = secp256k1.verify_recover(signature, digest)

    if not pubkey:
        raise wire.ProcessError("Invalid signature")

    if script_type == SPENDADDRESS:
        addr = address_pkh(pubkey, coin)
        if coin.cashaddr_prefix is not None:
            addr = address_to_cashaddr(addr, coin)
    elif script_type == SPENDP2SHWITNESS:
        addr = address_p2wpkh_in_p2sh(pubkey, coin)
    elif script_type == SPENDWITNESS:
        addr = address_p2wpkh(pubkey, coin)
    else:
        raise wire.ProcessError("Invalid signature")

    if addr != address:
        raise wire.ProcessError("Invalid signature")

    await require_confirm_verify_message(
        ctx, address_short(coin, address), coin.coin_shortcut, message
    )

    return Success(message="Message verified")
