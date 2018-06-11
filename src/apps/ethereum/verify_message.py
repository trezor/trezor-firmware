from ubinascii import hexlify
from trezor.crypto.curve import secp256k1
from trezor.crypto.hashlib import sha3_256
from trezor import ui
from trezor.ui.text import Text
from trezor.messages.Success import Success
from apps.common.confirm import require_confirm
from apps.common.display_address import split_address
from apps.common.signverify import split_message
from apps.ethereum.sign_message import message_digest


async def ethereum_verify_message(ctx, msg):

    digest = message_digest(msg.message)
    sig = bytearray([msg.signature[64]]) + msg.signature[:64]
    pubkey = secp256k1.verify_recover(sig, digest)

    if not pubkey:
        raise ValueError('Invalid signature')

    pkh = sha3_256(pubkey[1:]).digest(True)[-20:]

    if msg.address != pkh:
        raise ValueError('Invalid signature')

    address = '0x' + hexlify(msg.address).decode()

    await require_confirm_verify_message(ctx, address, msg.message)

    return Success(message='Message verified')


async def require_confirm_verify_message(ctx, address, message):
    lines = split_address(address)
    content = Text('Confirm address', ui.ICON_DEFAULT, ui.MONO, *lines)
    await require_confirm(ctx, content)

    message = split_message(message)
    content = Text('Verify message', ui.ICON_DEFAULT, max_lines=5, *message)
    await require_confirm(ctx, content)
