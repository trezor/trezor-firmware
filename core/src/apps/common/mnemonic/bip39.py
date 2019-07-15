from trezor.crypto import bip39
from trezor.errors import MnemonicError

from apps.common import mnemonic, storage


def get_type() -> int:
    return mnemonic.TYPE_BIP39


def process_single(mnemonic: str) -> bytes:
    """
    Receives single mnemonic and processes it. Returns what is then stored
    in the storage, which is the mnemonic itself for BIP-39.
    """
    if not bip39.check(mnemonic):
        raise MnemonicError()
    return mnemonic.encode()


def process_all(mnemonics: list) -> bytes:
    """
    Receives all mnemonics (just one in case of BIP-39) and processes it into a master
    secret which is usually then stored in storage.
    """
    return mnemonics[0].encode()


def store(secret: bytes, needs_backup: bool, no_backup: bool) -> None:
    storage.device.store_mnemonic_secret(
        secret, mnemonic.TYPE_BIP39, needs_backup, no_backup
    )


def get_seed(secret: bytes, passphrase: str, progress_bar: bool = True) -> bytes:
    if progress_bar:
        mnemonic._start_progress()
        seed = bip39.seed(secret.decode(), passphrase, mnemonic._render_progress)
        mnemonic._stop_progress()
    else:
        seed = bip39.seed(secret.decode(), passphrase)
    return seed
