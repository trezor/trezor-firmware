from micropython import const

import storage.resident_credentials
from storage.resident_credentials import MAX_RESIDENT_CREDENTIALS

from .credential import Fido2Credential

if False:
    from typing import Iterator


RP_ID_HASH_LENGTH = const(32)


def _credential_from_data(index: int, data: bytes) -> Fido2Credential:
    rp_id_hash = data[:RP_ID_HASH_LENGTH]
    cred_id = data[RP_ID_HASH_LENGTH:]
    cred = Fido2Credential.from_cred_id(cred_id, rp_id_hash)
    cred.index = index
    return cred


def find_all() -> Iterator[Fido2Credential]:
    for index in range(MAX_RESIDENT_CREDENTIALS):
        data = storage.resident_credentials.get(index)
        if data is not None:
            yield _credential_from_data(index, data)


def find_by_rp_id_hash(rp_id_hash: bytes) -> Iterator[Fido2Credential]:
    for index in range(MAX_RESIDENT_CREDENTIALS):
        data = storage.resident_credentials.get(index)

        if data is None:
            # empty slot
            continue

        if data[:RP_ID_HASH_LENGTH] != rp_id_hash:
            # rp_id_hash mismatch
            continue

        yield _credential_from_data(index, data)


def get_resident_credential(index: int) -> Fido2Credential | None:
    if not 0 <= index < MAX_RESIDENT_CREDENTIALS:
        return None

    data = storage.resident_credentials.get(index)
    if data is None:
        return None

    return _credential_from_data(index, data)


def store_resident_credential(cred: Fido2Credential) -> bool:
    slot = None
    for index in range(MAX_RESIDENT_CREDENTIALS):
        stored_data = storage.resident_credentials.get(index)
        if stored_data is None:
            # found candidate empty slot
            if slot is None:
                slot = index
            continue

        if cred.rp_id_hash != stored_data[:RP_ID_HASH_LENGTH]:
            # slot is occupied by a different rp_id_hash
            continue

        stored_cred = _credential_from_data(index, stored_data)
        # If a credential for the same RP ID and user ID already exists, then overwrite it.
        if stored_cred.user_id == cred.user_id:
            slot = index
            break

    if slot is None:
        return False

    cred_data = cred.rp_id_hash + cred.id
    storage.resident_credentials.set(slot, cred_data)
    return True
