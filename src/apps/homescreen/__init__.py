from trezor import config, utils, wire
from trezor.wire import register, protobuf_workflow
from trezor.messages import wire_types
from trezor.messages.Features import Features
from trezor.messages.Success import Success

from apps.common import storage, cache


def get_features():
    f = Features()
    f.vendor = 'trezor.io'
    f.language = 'english'
    f.major_version = utils.symbol('VERSION_MAJOR')
    f.minor_version = utils.symbol('VERSION_MINOR')
    f.patch_version = utils.symbol('VERSION_PATCH')
    f.revision = utils.symbol('GITREV')
    f.model = utils.model()
    if f.model == 'EMU':
        f.model = 'T'  # emulator currently emulates model T
    f.device_id = storage.get_device_id()
    f.label = storage.get_label()
    f.initialized = storage.is_initialized()
    f.pin_protection = config.has_pin()
    f.pin_cached = config.has_pin()
    f.passphrase_protection = storage.has_passphrase()
    f.passphrase_cached = cache.has_passphrase()
    f.needs_backup = storage.needs_backup()
    f.unfinished_backup = storage.unfinished_backup()
    f.flags = storage.get_flags()
    return f


async def handle_Initialize(ctx, msg):
    if msg.state is None or msg.state != cache.get_state(prev_state=bytes(msg.state)):
        cache.clear(msg.skip_passphrase)
    return get_features()


async def handle_GetFeatures(ctx, msg):
    return get_features()


async def handle_Cancel(ctx, msg):
    raise wire.ActionCancelled('Cancelled')


async def handle_ClearSession(ctx, msg):
    cache.clear()
    return Success(message='Session cleared')


async def handle_Ping(ctx, msg):
    if msg.button_protection:
        from apps.common.confirm import require_confirm
        from trezor.messages.ButtonRequestType import ProtectCall
        from trezor.ui.text import Text
        from trezor import ui
        await require_confirm(ctx, Text('Confirm', ui.ICON_DEFAULT), ProtectCall)
    if msg.passphrase_protection:
        from apps.common.request_passphrase import protect_by_passphrase
        await protect_by_passphrase(ctx)
    return Success(message=msg.message)


def boot():
    register(wire_types.Initialize, protobuf_workflow, handle_Initialize)
    register(wire_types.GetFeatures, protobuf_workflow, handle_GetFeatures)
    register(wire_types.Cancel, protobuf_workflow, handle_Cancel)
    register(wire_types.ClearSession, protobuf_workflow, handle_ClearSession)
    register(wire_types.Ping, protobuf_workflow, handle_Ping)
