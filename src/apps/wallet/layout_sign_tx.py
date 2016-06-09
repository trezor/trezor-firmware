from trezor import wire, ui
from trezor.utils import unimport_gen


@unimport_gen
def layout_sign_tx(message):
    ui.clear()
    print('sending')
