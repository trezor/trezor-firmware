from trezor.crypto import bip39, slip39
from trezor.errors import MnemonicError

from apps.common import storage

if False:
    from typing import Optional


def process_share(mnemonic: str, mnemonic_type: int):
    if mnemonic_type == mnemonic.TYPE_BIP39:
        return _process_bip39(mnemonic)
    else:
        return _process_slip39(mnemonic)


def _process_bip39(mnemonic: str) -> bytes:
    """
    Receives single mnemonic and processes it. Returns what is then stored
    in the storage, which is the mnemonic itself for BIP-39.
    """
    if not bip39.check(mnemonic):
        raise MnemonicError()
    return mnemonic.encode()


def _process_slip39(mnemonic: str) -> Optional[bytes]:
    """
    Receives single mnemonic and processes it. Returns what is then stored in storage or
    None if more shares are needed.
    """
    identifier, iteration_exponent, _, _, _, index, threshold, value = slip39.decode_mnemonic(
        mnemonic
    )  # TODO: use better data structure for this
    if threshold == 1:
        raise ValueError("Threshold equal to 1 is not allowed.")

    # if this is the first share, parse and store metadata
    if not storage.slip39.get_remaining():
        storage.slip39.set_iteration_exponent(iteration_exponent)
        storage.slip39.set_identifier(identifier)
        storage.slip39.set_threshold(threshold)
        storage.slip39.set_remaining(threshold - 1)
        storage.slip39_mnemonics.set(index, mnemonic)
        return None  # we need more shares

    # These should be checked by UI before so it's a Runtime exception otherwise
    if identifier != storage.slip39.get_identifier():
        raise RuntimeError("Slip39: Share identifiers do not match")
    if storage.slip39_mnemonics.get(index):
        raise RuntimeError("Slip39: This mnemonic was already entered")

    # add mnemonic to storage
    remaining = storage.slip39.get_remaining() - 1
    storage.slip39.set_remaining(remaining)
    storage.slip39_mnemonics.set(index, mnemonic)
    if remaining != 0:
        return None  # we need more shares

    # combine shares and return the master secret
    mnemonics = storage.slip39_mnemonics.fetch()
    identifier, iteration_exponent, secret = slip39.combine_mnemonics(mnemonics)
    storage.slip39.set_iteration_exponent(iteration_exponent)
    storage.slip39.set_identifier(identifier)
    return secret
