from trezor.dispatcher import register
from trezor.utils import unimport_func


@unimport_func
def dispatch_LoadDevice(mtype, mbuf):
    from trezor.messages.LoadDevice import LoadDevice

    message = LoadDevice.loads(mbuf)

    from .layout_load_device import layout_load_device
    return layout_load_device(message)


def boot():
    LoadDevice = 13
    register(LoadDevice, dispatch_LoadDevice)
