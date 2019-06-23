from trezor.crypto import bip39

from apps.common import mnemonic, storage


def get_type():
    return mnemonic.TYPE_BIP39


def process_single(mnemonic: str) -> bytes:
    """
    Receives single mnemonic and processes it. Returns what is then stored in storage or
    None if more shares are needed.
    """
    return mnemonic.encode()


def process_all(mnemonics: list) -> bytes:
    """
    Receives all mnemonics (just one in case of BIP-39) and processes it into a master
    secret which is usually then stored in storage.
    """
    return mnemonics[0].encode()


def store(secret: bytes, needs_backup: bool, no_backup: bool):
    storage.store_mnemonic(secret, mnemonic.TYPE_BIP39, needs_backup, no_backup)


def get_seed(secret: bytes, passphrase: str):
    mnemonic._start_progress()
    return bip39.seed(secret.decode(), passphrase, mnemonic._render_progress)


def check(secret: bytes):
    return bip39.check(secret)
