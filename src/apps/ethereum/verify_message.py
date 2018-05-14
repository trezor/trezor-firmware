# TODO: not currently enabled, waits for https://github.com/ethereum/EIPs/pull/712


async def ethereum_verify_message(ctx, msg):
    from .sign_message import message_digest
    from trezor.crypto.curve import secp256k1
    from trezor.crypto.hashlib import sha3_256
    from trezor import ui
    from trezor.messages.Success import Success

    digest = message_digest(msg.message)
    sig = bytearray([msg.signature[64]]) + msg.signature[:64]
    pubkey = secp256k1.verify_recover(sig, digest)

    if not pubkey:
        raise ValueError('Invalid signature')

    pkh = sha3_256(pubkey[1:]).digest(True)[-20:]

    if msg.address != pkh:
        raise ValueError('Invalid signature')

    ui.display.clear()
    ui.display.text(10, 30, 'Verifying message',
                    ui.BOLD, ui.LIGHT_GREEN, ui.BG)
    ui.display.text(10, 60, msg.message, ui.MONO, ui.FG, ui.BG)
    ui.display.text(10, 80, msg.address, ui.MONO, ui.FG, ui.BG)

    return Success(message='Message verified')
