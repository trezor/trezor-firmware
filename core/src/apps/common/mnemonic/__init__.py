from micropython import const

from trezor import ui, wire
from trezor.crypto.hashlib import sha256
from trezor.messages.Success import Success
from trezor.utils import consteq

from . import bip39, slip39

from apps.common import storage

TYPE_BIP39 = const(0)
TYPE_SLIP39 = const(1)

TYPES_WORD_COUNT = {12: bip39, 18: bip39, 24: bip39, 20: slip39, 33: slip39}


def get() -> (bytes, int):
    mnemonic_secret = storage.get_mnemonic_secret()
    mnemonic_type = storage.get_mnemonic_type() or TYPE_BIP39
    return mnemonic_secret, mnemonic_type


def get_seed(passphrase: str = ""):
    mnemonic_secret, mnemonic_type = get()
    if mnemonic_type == TYPE_BIP39:
        return bip39.get_seed(mnemonic_secret, passphrase)
    elif mnemonic_type == TYPE_SLIP39:
        return slip39.get_seed(mnemonic_secret, passphrase)


def dry_run(secret: bytes):
    digest_input = sha256(secret).digest()
    stored, _ = get()
    digest_stored = sha256(stored).digest()
    if consteq(digest_stored, digest_input):
        return Success(message="The seed is valid and matches the one in the device")
    else:
        raise wire.ProcessError(
            "The seed is valid but does not match the one in the device"
        )


def module_from_words_count(count: int):
    return TYPES_WORD_COUNT[count]


def _start_progress():
    ui.backlight_fade(ui.BACKLIGHT_DIM)
    ui.display.clear()
    ui.header("Please wait")
    ui.display.refresh()
    ui.backlight_fade(ui.BACKLIGHT_NORMAL)


def _render_progress(progress: int, total: int):
    p = 1000 * progress // total
    ui.display.loader(p, False, 18, ui.WHITE, ui.BG)
    ui.display.refresh()
