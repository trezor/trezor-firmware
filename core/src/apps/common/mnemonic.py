from trezor import ui, workflow
from trezor.crypto import bip39, slip39
from trezor.messages import BackupType

from apps.common import storage

if False:
    from typing import Optional, Tuple
    from apps.management.recovery_device.backup_types import BackupTypeUnion


def get() -> Tuple[Optional[bytes], int]:
    return get_secret(), get_type()


def get_secret() -> Optional[bytes]:
    return storage.device.get_mnemonic_secret()


def get_type() -> BackupTypeUnion:
    return storage.device.get_backup_type()


def is_bip39() -> bool:
    """
    If False then SLIP-39 (either Basic or Advanced).
    Other invalid values are checked directly in storage.
    """
    return get_type() == BackupType.Bip39


def get_seed(passphrase: str = "", progress_bar: bool = True) -> bytes:
    mnemonic_secret = get_secret()
    if mnemonic_secret is None:
        raise ValueError("Mnemonic not set")

    render_func = None
    if progress_bar:
        _start_progress()
        render_func = _render_progress

    if is_bip39():
        seed = bip39.seed(mnemonic_secret.decode(), passphrase, render_func)

    else:  # SLIP-39
        identifier = storage.device.get_slip39_identifier()
        iteration_exponent = storage.device.get_slip39_iteration_exponent()
        if identifier is None or iteration_exponent is None:
            # Identifier or exponent expected but not found
            raise RuntimeError
        seed = slip39.decrypt(
            identifier, iteration_exponent, mnemonic_secret, passphrase.encode()
        )

    return seed


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
