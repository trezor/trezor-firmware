from micropython import const

from apps.common.storage import common
from apps.webauthn.credential import Credential, Fido2Credential

if False:
    from typing import List, Optional

_RESIDENT_CREDENTIAL_START_KEY = const(1)
_MAX_RESIDENT_CREDENTIALS = const(16)


def get_resident_credentials(rp_id_hash: Optional[bytes]) -> List[Credential]:
    creds = []  # type: List[Credential]
    for i in range(
        _RESIDENT_CREDENTIAL_START_KEY,
        _RESIDENT_CREDENTIAL_START_KEY + _MAX_RESIDENT_CREDENTIALS,
    ):
        stored_cred_data = common._get(common._APP_FIDO2, i)
        if stored_cred_data is None:
            continue

        stored_rp_id_hash = stored_cred_data[:32]
        stored_cred_id = stored_cred_data[32:]

        if rp_id_hash is not None and rp_id_hash != stored_rp_id_hash:
            # Stored credential is not for this RP ID.
            continue

        stored_cred = Fido2Credential.from_cred_id(stored_cred_id, stored_rp_id_hash)
        if stored_cred is not None:
            creds.append(stored_cred)

    return creds


def store_resident_credential(cred: Fido2Credential) -> bool:
    slot = None
    for i in range(
        _RESIDENT_CREDENTIAL_START_KEY,
        _RESIDENT_CREDENTIAL_START_KEY + _MAX_RESIDENT_CREDENTIALS,
    ):
        stored_cred_data = common._get(common._APP_FIDO2, i)
        if stored_cred_data is None:
            if slot is None:
                slot = i
            continue

        stored_rp_id_hash = stored_cred_data[:32]
        stored_cred_id = stored_cred_data[32:]

        if cred.rp_id_hash != stored_rp_id_hash:
            # Stored credential is not for this RP ID.
            continue

        stored_cred = Fido2Credential.from_cred_id(stored_cred_id, stored_rp_id_hash)
        if stored_cred is None:
            # Stored credential is not for this RP ID.
            continue

        # If a credential for the same RP ID and user ID already exists, then overwrite it.
        if stored_cred.user_id == cred.user_id:
            slot = i
            break

    if slot is None:
        return False

    common._set(common._APP_FIDO2, slot, cred.rp_id_hash + cred.id)
    return True


def erase_resident_credentials() -> None:
    for i in range(
        _RESIDENT_CREDENTIAL_START_KEY,
        _RESIDENT_CREDENTIAL_START_KEY + _MAX_RESIDENT_CREDENTIALS,
    ):
        common._delete(common._APP_FIDO2, i)
