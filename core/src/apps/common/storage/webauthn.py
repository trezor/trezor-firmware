from micropython import const

from trezor.crypto import hashlib

from apps.common.storage import common
from apps.webauthn.credential import Fido2Credential

if False:
    from typing import List

_RESIDENT_CREDENTIAL_START_KEY = const(1)
_MAX_RESIDENT_CREDENTIALS = const(16)


def get_resident_credentials(rp_id_hash: bytes) -> List[Credential]:
    creds = []
    for i in range(
        _RESIDENT_CREDENTIAL_START_KEY,
        _RESIDENT_CREDENTIAL_START_KEY + _MAX_RESIDENT_CREDENTIALS,
    ):
        stored_credential_id = common._get(common._APP_FIDO2, i)
        if stored_credential_id is None:
            continue

        stored_cred = Fido2Credential.from_cred_id(stored_credential_id, rp_id_hash)
        if stored_cred is not None:
            creds.append(stored_cred)

    return creds


def store_resident_credential(cred: Fido2Credential) -> bool:
    slot = None
    rp_id_hash = hashlib.sha256(cred.rp_id.encode()).digest()
    for i in range(
        _RESIDENT_CREDENTIAL_START_KEY,
        _RESIDENT_CREDENTIAL_START_KEY + _MAX_RESIDENT_CREDENTIALS,
    ):
        # If a credential for the same RP ID and user ID already exists, then overwrite it.
        stored_credential_id = common._get(common._APP_FIDO2, i)
        if stored_credential_id is None:
            if slot is None:
                slot = i
            continue

        stored_cred = Fido2Credential.from_cred_id(stored_credential_id, rp_id_hash)
        if stored_cred is None:
            # Stored credential is not for this RP ID.
            continue

        if stored_cred.user_id == cred.user_id:
            slot = i
            break

    if slot is None:
        return False

    common._set(common._APP_FIDO2, slot, cred.id)
    return True


def erase_resident_credentials() -> None:
    for i in range(
        _RESIDENT_CREDENTIAL_START_KEY,
        _RESIDENT_CREDENTIAL_START_KEY + _MAX_RESIDENT_CREDENTIALS,
    ):
        common._delete(common._APP_FIDO2, i)
