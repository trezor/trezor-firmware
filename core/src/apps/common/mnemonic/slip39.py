from trezor.crypto import slip39

from apps.common import mnemonic, storage

if False:
    from typing import Optional


def generate_from_secret(master_secret: bytes, count: int, threshold: int) -> list:
    """
    Generates new Shamir backup for 'master_secret'. Multiple groups are not yet supported.
    """
    return slip39.generate_single_group_mnemonics_from_data(
        master_secret, storage.slip39.get_identifier(), threshold, count
    )


def get_type() -> int:
    return mnemonic.TYPE_SLIP39


def process_single(mnemonic: str) -> Optional[bytes]:
    """
    Receives single mnemonic and processes it. Returns what is then stored in storage or
    None if more shares are needed.
    """
    identifier, iteration_exponent, _, _, _, index, threshold, value = slip39.decode_mnemonic(
        mnemonic
    )  # TODO: use better data structure for this
    if threshold == 1:
        raise ValueError("Threshold equal to 1 is not allowed.")

    # if recovery is not in progress already, start it and wait for more mnemonics
    if not storage.slip39.is_in_progress():
        storage.slip39.set_in_progress(True)
        storage.slip39.set_iteration_exponent(iteration_exponent)
        storage.slip39.set_identifier(identifier)
        storage.slip39.set_threshold(threshold)
        storage.slip39.set_remaining(threshold - 1)
        storage.slip39.set_words_count(len(mnemonic.split()))
        storage.slip39_mnemonics.set(index, mnemonic)
        return None  # we need more shares

    # check identifier and member index of this share against stored values
    if identifier != storage.slip39.get_identifier():
        # TODO: improve UX (tell user)
        raise ValueError("Share identifiers do not match")
    if storage.slip39_mnemonics.get(index):
        # TODO: improve UX (tell user)
        raise ValueError("This mnemonic was already entered")

    # append to storage
    remaining = storage.slip39.get_remaining() - 1
    storage.slip39.set_remaining(remaining)
    storage.slip39.set(index, mnemonic)
    if remaining != 0:
        return None  # we need more shares

    # combine shares and return the master secret
    mnemonics = storage.slip39_mnemonics.fetch()
    if len(mnemonics) != threshold:
        raise ValueError("Some mnemonics are still missing.")
    _, _, secret = slip39.combine_mnemonics(mnemonics)
    return secret


def process_all(mnemonics: list) -> bytes:
    """
    Receives all mnemonics and processes it into pre-master secret which is usually then
    stored in the storage.
    """
    identifier, iteration_exponent, secret = slip39.combine_mnemonics(mnemonics)
    storage.slip39.set_iteration_exponent(iteration_exponent)
    storage.slip39.set_identifier(identifier)
    return secret


def store(secret: bytes, needs_backup: bool, no_backup: bool) -> None:
    storage.device.store_mnemonic_secret(
        secret, mnemonic.TYPE_SLIP39, needs_backup, no_backup
    )
    storage.slip39.delete_progress()


def get_seed(
    encrypted_master_secret: bytes, passphrase: str, progress_bar: bool = True
) -> bytes:
    if progress_bar:
        mnemonic._start_progress()
    identifier = storage.slip39.get_identifier()
    iteration_exponent = storage.slip39.get_iteration_exponent()

    master_secret = slip39.decrypt(
        identifier, iteration_exponent, encrypted_master_secret, passphrase
    )
    if progress_bar:
        mnemonic._stop_progress()
    return master_secret


def get_mnemonic_threshold(mnemonic: str) -> int:
    _, _, _, _, _, _, threshold, _ = slip39.decode_mnemonic(mnemonic)
    return threshold
