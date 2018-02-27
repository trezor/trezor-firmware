from trezor import config
from trezor.utils import unimport, symbol
from trezor.wire import register, protobuf_workflow
from trezor.messages import wire_types
from trezor.messages.Features import Features
from trezor.messages.Success import Success

from apps.common import storage, coins, cache


async def respond_Features(ctx, msg):

    if msg.__qualname__ == 'Initialize':
        if msg.state is None or msg.state != cache.get_state(salt=msg.state[:32]):
            cache.clear()

    f = Features()
    f.vendor = 'trezor.io'
    f.revision = symbol('GITREV')
    f.major_version = symbol('VERSION_MAJOR')
    f.minor_version = symbol('VERSION_MINOR')
    f.patch_version = symbol('VERSION_PATCH')
    f.model = 'T'
    f.coins = coins.COINS

    f.device_id = storage.get_device_id()
    f.label = storage.get_label()
    f.initialized = storage.is_initialized()
    f.passphrase_protection = storage.has_passphrase()
    f.pin_protection = config.has_pin()
    f.flags = storage.get_flags()
    f.language = 'english'

    f.state = cache.get_state()

    return f


async def respond_ClearSession(ctx, msg):
    cache.clear()
    return Success(message='Session cleared')


@unimport
async def respond_Pong(ctx, msg):

    if msg.button_protection:
        from apps.common.confirm import require_confirm
        from trezor.messages.ButtonRequestType import ProtectCall
        from trezor.ui.text import Text
        from trezor import ui
        await require_confirm(ctx, Text('Confirm', ui.ICON_DEFAULT), ProtectCall)

    if msg.passphrase_protection:
        from apps.common.request_passphrase import protect_by_passphrase
        await protect_by_passphrase(ctx)

    return Success(messge=msg.message)


def boot():
    register(wire_types.Initialize, protobuf_workflow, respond_Features)
    register(wire_types.GetFeatures, protobuf_workflow, respond_Features)
    register(wire_types.ClearSession, protobuf_workflow, respond_ClearSession)
    register(wire_types.Ping, protobuf_workflow, respond_Pong)
