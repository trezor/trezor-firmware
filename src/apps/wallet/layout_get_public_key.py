from trezor import wire
from trezor.utils import unimport_gen


@unimport_gen
def request_pin():
    from trezor.ui.pin import PinMatrix
    from trezor.ui.confirm import ConfirmDialog, CONFIRMED
    from trezor.messages.ButtonRequest import ButtonRequest
    from trezor.messages.ButtonRequestType import ProtectCall
    from trezor.messages.ButtonAck import ButtonAck

    matrix = PinMatrix()
    dialog = ConfirmDialog(matrix)
    dialog.render()

    ack = yield from wire.call(ButtonRequest(code=ProtectCall), ButtonAck)
    res = yield from dialog.wait()

    return matrix.pin if res == CONFIRMED else None


@unimport_gen
def layout_get_public_key(message):

    pin = yield from request_pin()

    if pin is not None:
        from trezor.messages.PublicKey import PublicKey
        from trezor.messages.HDNodeType import HDNodeType
        pubkey = PublicKey()
        pubkey.node = HDNodeType()
        pubkey.node.depth = 0
        pubkey.node.child_num = 0
        pubkey.node.fingerprint = 0
        pubkey.node.chain_code = 'deadbeef'
        pubkey.node.public_key = 'deadbeef'
        wire.write(pubkey)

    else:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import ActionCancelled
        wire.write(Failure(message='Cancelled', code=ActionCancelled))
