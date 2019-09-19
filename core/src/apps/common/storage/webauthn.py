from micropython import const

from apps.common.storage import common
from apps.webauthn.credential import Credential, Fido2Credential

if False:
    from typing import List, Optional

_RESIDENT_CREDENTIAL_START_KEY = const(1)
_MAX_RESIDENT_CREDENTIALS = const(16)


def get_resident_credentials(rp_id_hash: Optional[bytes] = None) -> List[Credential]:
    creds = []  # type: List[Credential]
    for i in range(_MAX_RESIDENT_CREDENTIALS):
        cred = get_resident_credential(i, rp_id_hash)
        if cred is not None:
            creds.append(cred)
    return creds


def get_resident_credential(
    index: int, rp_id_hash: Optional[bytes] = None
) -> Optional[Credential]:
    if not (0 <= index < _MAX_RESIDENT_CREDENTIALS):
        return None

    stored_cred_data = common.get(
        common.APP_WEBAUTHN, index + _RESIDENT_CREDENTIAL_START_KEY
    )
    if stored_cred_data is None:
        return None

    stored_rp_id_hash = stored_cred_data[:32]
    stored_cred_id = stored_cred_data[32:]

    if rp_id_hash is not None and rp_id_hash != stored_rp_id_hash:
        # Stored credential is not for this RP ID.
        return None

    stored_cred = Fido2Credential.from_cred_id(stored_cred_id, stored_rp_id_hash)
    if stored_cred is None:
        return None

    stored_cred.index = index
    return stored_cred


def store_resident_credential(cred: Fido2Credential) -> bool:
    slot = None
    for i in range(_MAX_RESIDENT_CREDENTIALS):
        stored_cred_data = common.get(
            common.APP_WEBAUTHN, i + _RESIDENT_CREDENTIAL_START_KEY
        )
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

    common.set(
        common.APP_WEBAUTHN,
        slot + _RESIDENT_CREDENTIAL_START_KEY,
        cred.rp_id_hash + cred.id,
    )
    return True


def erase_resident_credentials() -> None:
    for i in range(_MAX_RESIDENT_CREDENTIALS):
        common.delete(common.APP_WEBAUTHN, i + _RESIDENT_CREDENTIAL_START_KEY)


def erase_resident_credential(index: int) -> bool:
    if not (0 <= index < _MAX_RESIDENT_CREDENTIALS):
        return False
    common.delete(common.APP_WEBAUTHN, index + _RESIDENT_CREDENTIAL_START_KEY)
    return True
