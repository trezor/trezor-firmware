from micropython import const

from trezor import ui, workflow

from apps.common import storage
from apps.common.mnemonic import bip39, slip39

if False:
    from typing import Tuple, Union

TYPE_BIP39 = const(0)
TYPE_SLIP39 = const(1)

TYPES_WORD_COUNT = {12: bip39, 18: bip39, 24: bip39, 20: slip39, 33: slip39}


def get() -> Tuple[bytes, Union[bip39, slip39]]:
    mnemonic_secret = storage.device.get_mnemonic_secret()
    mnemonic_type = storage.device.get_mnemonic_type() or TYPE_BIP39
    if mnemonic_type not in (TYPE_BIP39, TYPE_SLIP39):
        raise RuntimeError("Invalid mnemonic type")
    if mnemonic_type == TYPE_BIP39:
        mnemonic_module = bip39
    else:
        mnemonic_module = slip39
    return mnemonic_secret, mnemonic_module


def get_seed(passphrase: str = "", progress_bar: bool = True) -> bytes:
    mnemonic_secret, mnemonic_module = get()
    if mnemonic_module == bip39:
        return bip39.get_seed(mnemonic_secret, passphrase, progress_bar)
    elif mnemonic_module == slip39:
        return slip39.get_seed(mnemonic_secret, passphrase, progress_bar)
    raise ValueError("Unknown mnemonic type")


def module_from_word_count(count: int) -> Union[bip39, slip39]:
    if count not in TYPES_WORD_COUNT:
        raise RuntimeError("Recovery: Unknown words count")
    return TYPES_WORD_COUNT[count]


def _start_progress() -> None:
    workflow.closedefault()
    ui.backlight_fade(ui.BACKLIGHT_DIM)
    ui.display.clear()
    ui.header("Please wait")
    ui.display.refresh()
    ui.backlight_fade(ui.BACKLIGHT_NORMAL)


def _render_progress(progress: int, total: int) -> None:
    p = 1000 * progress // total
    ui.display.loader(p, False, 18, ui.WHITE, ui.BG)
    ui.display.refresh()


def _stop_progress() -> None:
    pass
