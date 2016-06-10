from trezor.dispatcher import register
from trezor.utils import unimport_func


@unimport_func
def dispatch_LoadDevice(mtype, mbuf):
    from trezor.messages.LoadDevice import LoadDevice
    message = LoadDevice.loads(mbuf)
    from .layout_load_device import layout_load_device
    return layout_load_device(message)


@unimport_func
def dispatch_ResetDevice(mtype, mbuf):
    from trezor.messages.ResetDevice import ResetDevice
    message = ResetDevice.loads(mbuf)
    from .layout_reset_device import layout_reset_device
    return layout_reset_device(message)


@unimport_func
def dispatch_WipeDevice(mtype, mbuf):
    from trezor.messages.WipeDevice import WipeDevice
    message = WipeDevice.loads(mbuf)
    from .layout_wipe_device import layout_wipe_device
    return layout_wipe_device(message)


@unimport_func
def dispatch_RecoveryDevice(mtype, mbuf):
    from trezor.messages.RecoveryDevice import RecoveryDevice
    message = RecoveryDevice.loads(mbuf)
    from .layout_recovery_device import layout_recovery_device
    return layout_recovery_device(message)

def boot():
    LoadDevice = 13
    register(LoadDevice, dispatch_LoadDevice)
    ResetDevice = 14
    register(ResetDevice, dispatch_ResetDevice)
    WipeDevice = 5
    register(WipeDevice, dispatch_WipeDevice)
    RecoveryDevice = 45
    register(RecoveryDevice, dispatch_RecoveryDevice)