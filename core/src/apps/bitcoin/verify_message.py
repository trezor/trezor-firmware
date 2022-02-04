from typing import TYPE_CHECKING

from trezor import utils, wire
from trezor.crypto import base58
from trezor.crypto.curve import secp256k1
from trezor.enums import InputScriptType
from trezor.messages import Success
from trezor.ui.layouts import confirm_signverify, show_success

from apps.common import address_type, coins
from apps.common.signverify import decode_message, message_digest

from . import common
from .addresses import (
    address_p2wpkh,
    address_p2wpkh_in_p2sh,
    address_pkh,
    address_short,
    address_to_cashaddr,
)

if TYPE_CHECKING:
    from apps.common.coininfo import CoinInfo
    from trezor.messages import VerifyMessage


def address_to_script_type(address: str, coin: CoinInfo) -> InputScriptType:
    # Determines the script type from a non-multisig address.

    if coin.bech32_prefix and address.startswith(coin.bech32_prefix):
        witver, _ = common.decode_bech32_address(coin.bech32_prefix, address)
        if witver == 0:
            return InputScriptType.SPENDWITNESS
        elif witver == 1:
            return InputScriptType.SPENDTAPROOT
        else:
            raise wire.DataError("Invalid address")

    if (
        not utils.BITCOIN_ONLY
        and coin.cashaddr_prefix is not None
        and address.startswith(coin.cashaddr_prefix + ":")
    ):
        return InputScriptType.SPENDADDRESS

    try:
        raw_address = base58.decode_check(address, coin.b58_hash)
    except ValueError:
        raise wire.DataError("Invalid address")

    if address_type.check(coin.address_type, raw_address):
        # p2pkh
        return InputScriptType.SPENDADDRESS
    elif address_type.check(coin.address_type_p2sh, raw_address):
        # p2sh
        return InputScriptType.SPENDP2SHWITNESS

    raise wire.DataError("Invalid address")


async def verify_message(ctx: wire.Context, msg: VerifyMessage) -> Success:
    message = msg.message
    address = msg.address
    signature = msg.signature
    coin_name = msg.coin_name or "Bitcoin"
    coin = coins.by_name(coin_name)

    digest = message_digest(coin, message)

    script_type = address_to_script_type(address, coin)
    recid = signature[0]
    if 27 <= recid <= 34:
        # p2pkh or no script type provided
        pass  # use the script type from the address
    elif 35 <= recid <= 38 and script_type == InputScriptType.SPENDP2SHWITNESS:
        # segwit-in-p2sh
        signature = bytes([signature[0] - 4]) + signature[1:]
    elif 39 <= recid <= 42 and script_type == InputScriptType.SPENDWITNESS:
        # native segwit
        signature = bytes([signature[0] - 8]) + signature[1:]
    else:
        raise wire.ProcessError("Invalid signature")

    pubkey = secp256k1.verify_recover(signature, digest)

    if not pubkey:
        raise wire.ProcessError("Invalid signature")

    if script_type == InputScriptType.SPENDADDRESS:
        addr = address_pkh(pubkey, coin)
        if not utils.BITCOIN_ONLY and coin.cashaddr_prefix is not None:
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

    await show_success(ctx, "verify_message", "The signature is valid.")
    return Success(message="Message verified")
