from trezor.wire import register, protobuf_workflow
from trezor.utils import unimport
from trezor.messages.wire_types import \
    LoadDevice, ResetDevice, WipeDevice, RecoveryDevice, ApplySettings, ChangePin


@unimport
def dispatch_LoadDevice(*args, **kwargs):
    from .load_device import layout_load_device
    return layout_load_device(*args, **kwargs)


@unimport
def dispatch_ResetDevice(*args, **kwargs):
    from .reset_device import reset_device
    return reset_device(*args, **kwargs)


@unimport
def dispatch_WipeDevice(*args, **kwargs):
    from .wipe_device import layout_wipe_device
    return layout_wipe_device(*args, **kwargs)


@unimport
def dispatch_RecoveryDevice(*args, **kwargs):
    from .recovery_device import recovery_device
    return recovery_device(*args, **kwargs)


@unimport
def dispatch_ApplySettings(*args, **kwargs):
    from .apply_settings import layout_apply_settings
    return layout_apply_settings(*args, **kwargs)


@unimport
def dispatch_ChangePin(*args, **kwargs):
    from .change_pin import layout_change_pin
    return layout_change_pin(*args, **kwargs)


def boot():
    register(LoadDevice, protobuf_workflow, dispatch_LoadDevice)
    register(ResetDevice, protobuf_workflow, dispatch_ResetDevice)
    register(WipeDevice, protobuf_workflow, dispatch_WipeDevice)
    register(RecoveryDevice, protobuf_workflow, dispatch_RecoveryDevice)
    register(ApplySettings, protobuf_workflow, dispatch_ApplySettings)
    register(ChangePin, protobuf_workflow, dispatch_ChangePin)
