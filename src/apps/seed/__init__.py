from trezor.dispatcher import register
from trezor.utils import unimport_func


@unimport_func
def dispatch_Initialize(mtype, mbuf):
    from trezor.messages.Initialize import Initialize

    message = Initialize.loads(mbuf)

    from .layout_seed import layout_seed
    return layout_seed(message)


def boot():
    Initialize = 0
    # register(Initialize, dispatch_Initialize)
