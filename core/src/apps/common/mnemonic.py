import storage.device
from trezor import ui, utils, workflow
from trezor.enums import BackupType


def get() -> tuple[bytes | None, BackupType]:
    return get_secret(), get_type()


def get_secret() -> bytes | None:
    return storage.device.get_mnemonic_secret()


def get_type() -> BackupType:
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
        raise ValueError  # Mnemonic not set

    render_func = None
    if progress_bar and not utils.DISABLE_ANIMATION:
        _start_progress()
        render_func = _render_progress

    if is_bip39():
        from trezor.crypto import bip39

        seed = bip39.seed(mnemonic_secret.decode(), passphrase, render_func)

    else:  # SLIP-39
        from trezor.crypto import slip39

        identifier = storage.device.get_slip39_identifier()
        iteration_exponent = storage.device.get_slip39_iteration_exponent()
        if identifier is None or iteration_exponent is None:
            # Identifier or exponent expected but not found
            raise RuntimeError
        seed = slip39.decrypt(
            mnemonic_secret,
            passphrase.encode(),
            iteration_exponent,
            identifier,
            render_func,
        )

    return seed


if not utils.BITCOIN_ONLY:

    def derive_cardano_icarus(
        passphrase: str = "",
        trezor_derivation: bool = True,
        progress_bar: bool = True,
    ) -> bytes:
        if not is_bip39():
            raise ValueError  # should not be called for SLIP-39

        mnemonic_secret = get_secret()
        if mnemonic_secret is None:
            raise ValueError("Mnemonic not set")

        render_func = None
        if progress_bar and not utils.DISABLE_ANIMATION:
            _start_progress()
            render_func = _render_progress

        from trezor.crypto import cardano

        return cardano.derive_icarus(
            mnemonic_secret.decode(), passphrase, trezor_derivation, render_func
        )


def _start_progress() -> None:
    from trezor.ui.layouts import draw_simple_text

    # Because we are drawing to the screen manually, without a layout, we
    # should make sure that no other layout is running.
    workflow.close_others()
    draw_simple_text("Please wait")


def _render_progress(progress: int, total: int) -> None:
    p = 1000 * progress // total
    ui.display.loader(p, False, 18, ui.WHITE, ui.BG)
    ui.refresh()
