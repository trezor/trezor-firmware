from trezor import wire
from trezor.utils import unimport_gen
from trezor.workflows.request_pin import request_pin


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
        yield from wire.write(pubkey)

    else:
        from trezor.messages.Failure import Failure
        from trezor.messages.FailureType import ActionCancelled
        yield from wire.write(Failure(message='Cancelled', code=ActionCancelled))
