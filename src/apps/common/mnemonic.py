from trezor import ui
from trezor.crypto import bip39

from apps.common import storage

TYPE_BIP39 = 0


def get() -> (bytes, int):
    mnemonic_secret = storage.get_mnemonic_secret()
    mnemonic_type = storage.get_mnemonic_type()
    return mnemonic_secret, mnemonic_type


def get_seed(passphrase: str = ""):
    secret, mnemonic_type = get()
    _start_progress()
    if mnemonic_type == TYPE_BIP39:
        return bip39.seed(secret.decode(), passphrase, _render_progress)


def process(mnemonics: list, mnemonic_type: int):
    if mnemonic_type == TYPE_BIP39:
        return mnemonics[0].encode()
    else:
        raise RuntimeError("Unknown mnemonic type")


def restore() -> str:
    secret, mnemonic_type = get()
    if mnemonic_type == TYPE_BIP39:
        return secret.decode()


def _start_progress():
    ui.backlight_slide_sync(ui.BACKLIGHT_DIM)
    ui.display.clear()
    ui.header("Please wait")
    ui.display.refresh()
    ui.backlight_slide_sync(ui.BACKLIGHT_NORMAL)


def _render_progress(progress: int, total: int):
    p = int(1000 * progress / total)
    ui.display.loader(p, 18, ui.WHITE, ui.BG)
    ui.display.refresh()
