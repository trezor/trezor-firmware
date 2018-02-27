from trezor import ui, wire
from trezor.crypto import base58
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import ripemd160, sha256
from trezor.messages.FailureType import ProcessError
from trezor.messages.Success import Success
from trezor.ui.text import Text
from apps.common import address_type, coins
from apps.common.confirm import require_confirm
from apps.common.signverify import message_digest, split_message


async def verify_message(ctx, msg):
    message = msg.message
    address = msg.address
    signature = msg.signature
    coin_name = msg.coin_name or 'Bitcoin'
    coin = coins.by_name(coin_name)

    await confirm_verify_message(ctx, message)

    digest = message_digest(coin, message)
    pubkey = secp256k1.verify_recover(signature, digest)

    if not pubkey:
        raise wire.FailureError(ProcessError, 'Invalid signature')

    raw_address = base58.decode_check(address)
    _, pkh = address_type.split(coin, raw_address)
    pkh2 = ripemd160(sha256(pubkey).digest()).digest()

    if pkh != pkh2:
        raise wire.FailureError(ProcessError, 'Invalid signature')

    return Success(message='Message verified')


async def confirm_verify_message(ctx, message):
    message = split_message(message)
    content = Text('Verify message', ui.ICON_DEFAULT, max_lines=5, *message)
    await require_confirm(ctx, content)
