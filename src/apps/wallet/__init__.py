from trezor.dispatcher import register
from trezor.utils import unimport_func


@unimport_func
def dispatch_GetPublicKey(mtype, mbuf):
    from trezor.messages.GetPublicKey import GetPublicKey

    message = GetPublicKey.loads(mbuf)

    from .layout_get_public_key import layout_get_public_key
    return layout_get_public_key(message)


@unimport_func
def dispatch_SignTx(mtype, mbuf):
    from trezor.messages.SignTx import SignTx

    message = SignTx.loads(mbuf)

    from .layout_sign_tx import layout_sign_tx
    return layout_sign_tx(message)


def boot():
    GetPublicKey = 11
    register(GetPublicKey, dispatch_GetPublicKey)
    SignTx = 15
    register(SignTx, dispatch_SignTx)
