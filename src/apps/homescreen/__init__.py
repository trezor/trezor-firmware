from trezor import config
from trezor.wire import register, protobuf_workflow
from trezor.utils import unimport
from trezor.messages.wire_types import Initialize, GetFeatures, Ping, ClearSession


@unimport
async def respond_Features(ctx, msg):
    from apps.common import storage, coins, cache
    from trezor.messages.Features import Features

    if msg.__qualname__ == 'Initialize':
        if not hasattr(msg, 'state') or msg.state != cache.get_state():
            cache.clear()

    f = Features()
    f.vendor = 'trezor.io'
    f.revision = '0123456789'
    f.bootloader_hash = '0123456789'
    f.major_version = 2
    f.minor_version = 0
    f.patch_version = 0
    f.model = 'T'
    f.coins = coins.COINS

    f.device_id = storage.get_device_id()
    f.label = storage.get_label()
    f.initialized = storage.is_initialized()
    f.passphrase_protection = storage.has_passphrase()
    f.pin_protection = config.has_pin()
    f.language = 'english'

    f.state = cache.get_state()

    return f


@unimport
async def respond_Pong(ctx, msg):
    from trezor.messages.Success import Success

    s = Success()
    s.message = msg.message

    if msg.button_protection:
        from apps.common.confirm import require_confirm
        from trezor.messages.ButtonRequestType import ProtectCall
        from trezor.ui.text import Text
        from trezor import ui
        await require_confirm(ctx, Text('Confirm', ui.ICON_RESET), ProtectCall)

    if msg.passphrase_protection:
        from apps.common.request_passphrase import protect_by_passphrase
        await protect_by_passphrase(ctx)

    return s


@unimport
async def respond_ClearSession(ctx, msg):
    from apps.common import cache
    from trezor.messages.Success import Success
    cache.clear()
    return Success(message='Session cleared')


def boot():
    register(Initialize, protobuf_workflow, respond_Features)
    register(GetFeatures, protobuf_workflow, respond_Features)
    register(Ping, protobuf_workflow, respond_Pong)
    register(ClearSession, protobuf_workflow, respond_ClearSession)
