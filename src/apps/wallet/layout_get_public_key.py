from trezor import wire
from trezor import ui
from trezor.ui.button import Button, CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from trezor.ui.pin import PinDialog
from trezor.utils import unimport_gen


@unimport_gen
def layout_get_public_key(message):

    confirm = Button((0, 0, 240, 240), 'Export public key?',
                      normal_style=CONFIRM_BUTTON,
                      active_style=CONFIRM_BUTTON_ACTIVE)
    yield from confirm.wait()

    from trezor.messages.PublicKey import PublicKey
    from trezor.messages.HDNodeType import HDNodeType

    pubkey = PublicKey()
    pubkey.node = HDNodeType()
    pubkey.node.depth = 0
    pubkey.node.child_num = 0
    pubkey.node.fingerprint = 0
    pubkey.node.chain_code = 'deadbeef'
    pubkey.node.public_key = 'deadbeef'
    wire.write_msg(pubkey)
