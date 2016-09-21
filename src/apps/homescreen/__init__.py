from trezor.wire import register_type, protobuf_handler, write_message
from trezor.utils import unimport
from trezor.messages.wire_types import Initialize


@unimport
async def dispatch_Initialize(_, session_id):
    from trezor.messages.Features import Features
    features = Features(
        revision='deadbeef',
        bootloader_hash='deadbeef',
        device_id='DEADBEEF',
        coins=[],
        imported=False,
        initialized=False,
        label='My TREZOR',
        major_version=2,
        minor_version=0,
        patch_version=0,
        pin_cached=False,
        pin_protection=True,
        passphrase_cached=False,
        passphrase_protection=False,
        vendor='bitcointrezor.com')
    await write_message(session_id, features)


def boot():
    register_type(Initialize, protobuf_handler, dispatch_Initialize)
