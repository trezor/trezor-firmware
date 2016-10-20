from trezor.wire import register_type, protobuf_handler, write_message
from trezor.utils import unimport
from trezor.messages.wire_types import Initialize, GetFeatures


async def respond(_, session_id):
    from ..common import storage
    from trezor.messages.Features import Features

    f = Features()
    f.vendor = 'bitcointrezor.com'
    f.revision = '0123456789'
    f.bootloader_hash = '0123456789'
    f.major_version = 2
    f.minor_version = 0
    f.patch_version = 0
    f.coins = []

    f.device_id = storage.get_device_id()
    f.label = storage.get_label()
    f.initialized = storage.is_initialized()
    f.pin_protection = storage.is_protected_by_pin()
    f.passphrase_protection = storage.is_protected_by_passphrase()

    await write_message(session_id, f)


def boot():
    register_type(Initialize, protobuf_handler, respond)
    register_type(GetFeatures, protobuf_handler, respond)
