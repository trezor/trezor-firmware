from trezor.wire import register_type, protobuf_handler
from trezor.utils import unimport
from trezor.messages.wire_types import \
    LoadDevice, ResetDevice, WipeDevice, RecoveryDevice, ApplySettings


@unimport
def dispatch_LoadDevice(*args, **kwargs):
    from .layout_load_device import layout_load_device
    return layout_load_device(*args, **kwargs)


@unimport
def dispatch_ResetDevice(*args, **kwargs):
    from .layout_reset_device import layout_reset_device
    return layout_reset_device(*args, **kwargs)


@unimport
def dispatch_WipeDevice(*args, **kwargs):
    from .layout_wipe_device import layout_wipe_device
    return layout_wipe_device(*args, **kwargs)


@unimport
def dispatch_RecoveryDevice(*args, **kwargs):
    from .layout_recovery_device import layout_recovery_device
    return layout_recovery_device(*args, **kwargs)


@unimport
def dispatch_ApplySettings(*args, **kwargs):
    from .layout_apply_settings import layout_apply_settings
    return layout_apply_settings(*args, **kwargs)


def boot():
    register_type(LoadDevice, protobuf_handler, dispatch_LoadDevice)
    register_type(ResetDevice, protobuf_handler, dispatch_ResetDevice)
    register_type(WipeDevice, protobuf_handler, dispatch_WipeDevice)
    register_type(RecoveryDevice, protobuf_handler, dispatch_RecoveryDevice)
    register_type(ApplySettings, protobuf_handler, dispatch_ApplySettings)
