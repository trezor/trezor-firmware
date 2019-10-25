from micropython import const

from storage import common

if False:
    from typing import Optional


_RESIDENT_CREDENTIAL_START_KEY = const(1)

MAX_RESIDENT_CREDENTIALS = const(100)


def get_resident_credential(index: int) -> Optional[bytes]:
    if not (0 <= index < MAX_RESIDENT_CREDENTIALS):
        raise ValueError  # invalid credential index

    return common.get(common.APP_WEBAUTHN, index + _RESIDENT_CREDENTIAL_START_KEY)


def set_resident_credential(index: int, data: bytes) -> None:
    if not (0 <= index < MAX_RESIDENT_CREDENTIALS):
        raise ValueError  # invalid credential index

    common.set(common.APP_WEBAUTHN, index + _RESIDENT_CREDENTIAL_START_KEY, data)


def delete_resident_credential(index: int) -> None:
    if not (0 <= index < MAX_RESIDENT_CREDENTIALS):
        raise ValueError  # invalid credential index

    common.delete(common.APP_WEBAUTHN, index + _RESIDENT_CREDENTIAL_START_KEY)


def delete_all_resident_credentials() -> None:
    for i in range(MAX_RESIDENT_CREDENTIALS):
        common.delete(common.APP_WEBAUTHN, i + _RESIDENT_CREDENTIAL_START_KEY)
