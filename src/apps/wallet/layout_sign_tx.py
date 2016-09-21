from trezor import wire, ui
from trezor.utils import unimport


@unimport
def layout_sign_tx(message):
    ui.clear()
    print('sending')
