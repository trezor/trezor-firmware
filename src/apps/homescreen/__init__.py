from trezor.dispatcher import register
from trezor.utils import unimport_func


@unimport_func
def dispatch_Initialize(mtype, mbuf):
    from trezor.messages.Initialize import Initialize

    message = Initialize.loads(mbuf)

    from .layout_homescreen import layout_homescreen
    return layout_homescreen(message)


def boot():
    Initialize = 0
    register(Initialize, dispatch_Initialize)
