from trezor import wire
from trezor.crypto.curve import secp256k1
from trezor.enums import InputScriptType
from trezor.messages import Success
from trezor.ui.layouts import confirm_signverify

from apps.common import coins
from apps.common.signverify import decode_message, message_digest

from .addresses import (
    address_p2wpkh,
    address_p2wpkh_in_p2sh,
    address_pkh,
    address_short,
    address_to_cashaddr,
)

if False:
    from trezor.messages import VerifyMessage


async def verify_message(ctx: wire.Context, msg: VerifyMessage) -> Success:
    message = msg.message
    address = msg.address
    signature = msg.signature
    coin_name = msg.coin_name or "Bitcoin"
    coin = coins.by_name(coin_name)

    digest = message_digest(coin, message)

    recid = signature[0]
    if 27 <= recid <= 34:
        # p2pkh
        script_type = InputScriptType.SPENDADDRESS
    elif 35 <= recid <= 38:
        # segwit-in-p2sh
        script_type = InputScriptType.SPENDP2SHWITNESS
        signature = bytes([signature[0] - 4]) + signature[1:]
    elif 39 <= recid <= 42:
        # native segwit
        script_type = InputScriptType.SPENDWITNESS
        signature = bytes([signature[0] - 8]) + signature[1:]
    else:
        raise wire.ProcessError("Invalid signature")

    pubkey = secp256k1.verify_recover(signature, digest)

    if not pubkey:
        raise wire.ProcessError("Invalid signature")

    if script_type == InputScriptType.SPENDADDRESS:
        addr = address_pkh(pubkey, coin)
        if coin.cashaddr_prefix is not None:
            addr = address_to_cashaddr(addr, coin)
    elif script_type == InputScriptType.SPENDP2SHWITNESS:
        addr = address_p2wpkh_in_p2sh(pubkey, coin)
    elif script_type == InputScriptType.SPENDWITNESS:
        addr = address_p2wpkh(pubkey, coin)
    else:
        raise wire.ProcessError("Invalid signature")

    if addr != address:
        raise wire.ProcessError("Invalid signature")

    await confirm_signverify(
        ctx,
        coin.coin_shortcut,
        decode_message(message),
        address=address_short(coin, address),
        verify=True,
    )

    return Success(message="Message verified")
