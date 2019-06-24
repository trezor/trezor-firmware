from trezor.crypto import slip39

from apps.common import mnemonic, storage


def generate_from_secret(master_secret: bytes, count: int, threshold: int) -> str:
    """
    Generates new Shamir backup for 'master_secret'. Multiple groups are not yet supported.
    """
    identifier, group_mnemonics = slip39.generate_single_group_mnemonics_from_data(
        master_secret, threshold, count
    )
    storage.set_slip39_iteration_exponent(slip39.DEFAULT_ITERATION_EXPONENT)
    storage.set_slip39_identifier(identifier)
    return group_mnemonics


def get_type():
    return mnemonic.TYPE_SLIP39


def process_single(mnemonic: str) -> bytes:
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
    if not storage.is_slip39_in_progress():
        storage.set_slip39_in_progress(True)
        storage.set_slip39_iteration_exponent(iteration_exponent)
        storage.set_slip39_identifier(identifier)
        storage.set_slip39_threshold(threshold)
        storage.set_slip39_remaining(threshold - 1)
        storage.set_slip39_words_count(len(mnemonic.split()))
        storage.set_slip39_mnemonic(index, mnemonic)
        return None  # we need more shares

    # check identifier and member index of this share against stored values
    if identifier != storage.get_slip39_identifier():
        # TODO: improve UX (tell user)
        raise ValueError("Share identifiers do not match")
    if storage.get_slip39_mnemonic(index):
        # TODO: improve UX (tell user)
        raise ValueError("This mnemonic was already entered")

    # append to storage
    remaining = storage.get_slip39_remaining() - 1
    storage.set_slip39_remaining(remaining)
    storage.set_slip39_mnemonic(index, mnemonic)
    if remaining != 0:
        return None  # we need more shares

    # combine shares and return the master secret
    mnemonics = storage.get_slip39_mnemonics()
    if len(mnemonics) != threshold:
        raise ValueError("Some mnemonics are still missing.")
    _, _, secret = slip39.combine_mnemonics(mnemonics)
    return secret


def process_all(mnemonics: list) -> bytes:
    """
    Receives all mnemonics and processes it into pre-master secret which is usually then
    stored in the storage.
    """
    _, _, secret = slip39.combine_mnemonics(mnemonics)
    return secret


def store(secret: bytes, needs_backup: bool, no_backup: bool):
    storage.store_mnemonic(secret, mnemonic.TYPE_SLIP39, needs_backup, no_backup)
    storage.clear_slip39_data()


def get_seed(encrypted_master_secret: bytes, passphrase: str):
    mnemonic._start_progress()
    identifier = storage.get_slip39_identifier()
    iteration_exponent = storage.get_slip39_iteration_exponent()
    master_secret = slip39.decrypt(
        identifier, iteration_exponent, encrypted_master_secret, passphrase
    )
    mnemonic._stop_progress()
    return master_secret
