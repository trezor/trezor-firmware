from typing import List, Tuple

from storage import cache_codec, cache_common
from trezor import utils

FIELDS_TO_ENCRYPT = [cache_common.APP_COMMON_SEED]
if not utils.BITCOIN_ONLY:
    FIELDS_TO_ENCRYPT += [
        cache_common.APP_CARDANO_ICARUS_SECRET,
        cache_common.APP_CARDANO_ICARUS_TREZOR_SECRET,
    ]

FIELDS_TO_ENCRYPT_SESSIONLESS = [cache_common.APP_COMMON_SEED_WITHOUT_PASSPHRASE]


def is_empty(session: cache_codec.DataCache, fields_to_encrypt: List[int]) -> bool:
    """
    Checks if the session has no data set for the fields to encrypt.
    """
    for field in fields_to_encrypt:
        if session.get(field):
            return False
    return True


def get_seed_encryption_key(session_id: bytes) -> bytes:
    """
    Returns the seed encryption key for a given session ID.
    The key is derived from the device secret and the session ID.
    """
    from typing import TYPE_CHECKING

    from storage.device import get_device_secret

    from apps.common.seed import Slip21Node

    if TYPE_CHECKING:
        from apps.common.paths import Slip21Path

    device_secret = get_device_secret()
    label = b"Seed encryption key"
    path: Slip21Path = [label, session_id]
    key_node = Slip21Node(device_secret)
    key_node.derive_path(path)
    return key_node.key()


def chain_seed_values(
    session: cache_codec.DataCache, fileds_to_encrypt: List[int]
) -> bytes:
    """
    Creates a plaintext representation of the session's seed
    and other relevant data for encryption.

    :param session: The session containing the data to encrypt.
    :param fileds_to_encrypt: The list of fields to include in the plaintext.
    :return: A bytes object containing the concatenated values of the fields.
    """
    plaintext = bytearray()
    for field in fileds_to_encrypt:
        value = session.get(field)
        if value:
            plaintext += value
    return bytes(plaintext)


def parse_value_chain_to_cache(
    ciphertext: bytes, session: cache_codec.DataCache, fields_to_encrypt: List[int]
) -> None:
    """
    Parses the ciphertext and sets the values back into the session variables.
    It assumes that the ciphertext is a concatenation of the encrypted values
    for the fields to encrypt in the same order as they are defined.

    :param ciphertext: The encrypted data to parse.
    :param session: The session to set the decrypted values into.
    :param fields_to_encrypt: The list of fields to set in the session.
    """
    current_length = 0
    for field in fields_to_encrypt:
        value = session.get(field)
        if value:
            length = len(value)
            ciphered_value = ciphertext[current_length : current_length + length]
            session.set(field, ciphered_value)
            current_length += length
    if current_length != len(ciphertext):
        raise ValueError(
            f"Ciphertext length ({len(ciphertext)}) does not match expected length ({current_length})"
        )


def get_decryption_data(session: cache_codec.DataCache) -> Tuple[bytes, bytes]:
    """
    Retrieves the decryption data - nonce and tag - from the session attributes.
    These attributes are set during encryption and are used to decrypt the session's seeds.
    If the session does not contain encryption data, it raises an error.

    :raises ValueError: If the session does not contain encryption data.
    """
    try:
        tag: bytes = getattr(session, "encryption_tag")
        nonce: bytes = getattr(session, "encryption_nonce")
    except AttributeError:
        raise ValueError("No encryption data found for the session")
    return nonce, tag


def delete_decryption_data(session: cache_codec.DataCache) -> None:
    """
    Deletes the decryption data (nonce and tag) from the session attributes.
    This is used to free memory after decryption is done.
    If the session does not contain encryption data, it raises an error.

    :raises ValueError: If the session does not contain encryption data.
    """
    import gc

    try:
        delattr(session, "encryption_nonce")
        delattr(session, "encryption_tag")
        gc.collect()  # Force garbage collection to free memory
    except AttributeError:
        raise ValueError("No encryption data found for the session")


def set_decryption_data(
    session: cache_codec.DataCache, nonce: bytes, tag: bytes
) -> None:
    """
    Sets the decryption data (nonce and tag) as attributes of the session.
    These are later used to decrypt the session's seeds.
    Raises an error if the session already contains encryption data.

    :param session: The session to set the decryption data into.
    :param nonce: The 12-bytes nonce used for encryption.
    :param tag: The 16-bytes tag used for authentication.

    :raises ValueError: If the session already contains encryption data.
    """
    if hasattr(session, "encryption_nonce") or hasattr(session, "encryption_tag"):
        raise ValueError("Session already contains encryption data")
    setattr(session, "encryption_nonce", nonce)
    setattr(session, "encryption_tag", tag)


def get_common_data(session: cache_codec.DataCache) -> Tuple[bytes, List[int]]:
    """
    Retrieves the session ID and the fields to encrypt based on the DataCache type.
    For `SessionCache`, it uses the session ID of the session.
    For `SessionlessCache`, it uses a zeroed session ID.

    :return: the session ID and the list of fields to encrypt/decrypt
    based on the DataCache type.
    """

    if isinstance(session, cache_codec.SessionCache):
        session_id = session.export_session_id()
        fields_to_encrypt = FIELDS_TO_ENCRYPT
    elif isinstance(session, cache_common.SessionlessCache):
        session_id = b"\x00" * cache_codec.SESSION_ID_LENGTH
        fields_to_encrypt = FIELDS_TO_ENCRYPT_SESSIONLESS
    else:
        raise TypeError("Unsupported session type for encryption")

    return session_id, fields_to_encrypt


def encrypt_session_seeds(session: cache_codec.DataCache) -> None:
    """
    Encrypts the seeds and other relevant data in the DataCache.
    This function retrieves the session ID, derives the encryption key,
    and encrypts the seed values using ChaCha20-Poly1305.
    The encrypted data is then stored back in the session variables.
    It sets the nonce and tag for decryption later as attributes of the session.
    If there is nothing to encrypt, it does nothing.
    """
    from trezorcrypto import chacha20poly1305

    from trezor.crypto import random

    session_id, fields_to_encrypt = get_common_data(session)
    if is_empty(session, fields_to_encrypt):
        return

    encryption_key = get_seed_encryption_key(session_id)
    nonce = random.bytes(12, True)
    cipher = chacha20poly1305(encryption_key, nonce)
    ciphertext = cipher.encrypt(chain_seed_values(session, fields_to_encrypt))
    tag = cipher.finish()
    set_decryption_data(session, nonce, tag)
    parse_value_chain_to_cache(ciphertext, session, fields_to_encrypt)


def decrypt_session_seeds(session: cache_codec.DataCache) -> None:
    """
    Decrypts the seeds and other relevant data in the DataCache.
    This function retrieves the session ID, nonce, and tag,
    derives the decryption key, and decrypts the seed values using ChaCha20-Poly1305.
    The decrypted data is then parsed and stored back in the session variables.
    If there is nothing to decrypt, it does nothing.
    """
    from trezorcrypto import chacha20poly1305

    session_id, fields_to_decrypt = get_common_data(session)
    if is_empty(session, fields_to_decrypt):
        return

    nonce, tag = get_decryption_data(session)
    decryption_key = get_seed_encryption_key(session_id)
    cipher = chacha20poly1305(decryption_key, nonce)
    plaintext = cipher.decrypt(chain_seed_values(session, fields_to_decrypt))
    control_tag = cipher.finish()
    if control_tag != tag:
        raise ValueError("Decryption failed: tag mismatch")
    parse_value_chain_to_cache(plaintext, session, fields_to_decrypt)
    delete_decryption_data(session)
