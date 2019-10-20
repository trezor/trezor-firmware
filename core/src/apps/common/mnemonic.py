from micropython import const

from trezor import ui, workflow
from trezor.crypto import bip39, slip39

from apps.common import storage

if False:
    from typing import Optional, Tuple

TYPE_BIP39 = const(0)
TYPE_SLIP39 = const(1)

TYPES_WORD_COUNT = {
    12: TYPE_BIP39,
    18: TYPE_BIP39,
    24: TYPE_BIP39,
    20: TYPE_SLIP39,
    33: TYPE_SLIP39,
}


def get() -> Tuple[Optional[bytes], int]:
    return get_secret(), get_type()


def get_secret() -> Optional[bytes]:
    return storage.device.get_mnemonic_secret()


def get_type() -> int:
    mnemonic_type = storage.device.get_mnemonic_type() or TYPE_BIP39
    if mnemonic_type not in (TYPE_BIP39, TYPE_SLIP39):
        raise RuntimeError("Invalid mnemonic type")
    return mnemonic_type


def get_seed(passphrase: str = "", progress_bar: bool = True) -> bytes:
    mnemonic_secret, mnemonic_type = get()
    if mnemonic_secret is None:
        raise ValueError("Mnemonic not set")

    render_func = None
    if progress_bar:
        _start_progress()
        render_func = _render_progress

    if mnemonic_type == TYPE_BIP39:
        seed = bip39.seed(mnemonic_secret.decode(), passphrase, render_func)

    elif mnemonic_type == TYPE_SLIP39:
        identifier = storage.device.get_slip39_identifier()
        iteration_exponent = storage.device.get_slip39_iteration_exponent()
        if identifier is None or iteration_exponent is None:
            # Identifier or exponent expected but not found
            raise RuntimeError
        seed = slip39.decrypt(
            identifier, iteration_exponent, mnemonic_secret, passphrase.encode()
        )

    if progress_bar:
        _stop_progress()
    return seed


def type_from_word_count(count: int) -> int:
    if count not in TYPES_WORD_COUNT:
        raise RuntimeError("Recovery: Unknown words count")
    return TYPES_WORD_COUNT[count]


def _start_progress() -> None:
    # Because we are drawing to the screen manually, without a layout, we
    # should make sure that no other layout is running.  At this point, only
    # the homescreen should be on, so shut it down.
    workflow.close_default()
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
