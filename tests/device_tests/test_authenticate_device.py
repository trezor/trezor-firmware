import pytest

from trezorlib import device
from trezorlib.debuglink import SessionDebugWrapper as Session

from ..common import compact_size
from .certificate import check_signature_optiga, check_signature_tropic

pytestmark = pytest.mark.models("safe")


@pytest.mark.parametrize(
    "challenge",
    (
        b"",
        b"hello world",
        b"\x00" * 1024,
        bytes.fromhex(
            "21f3d40e63c304d0312f62eb824113efd72ba1ee02bef6777e7f8a7b6f67ba16"
        ),
    ),
)
def test_authenticate_device_optiga(session: Session, challenge: bytes) -> None:
    # NOTE Applications must generate a random challenge for each request.

    if not session.features.bootloader_locked:
        pytest.xfail("unlocked bootloader")

    # Issue an AuthenticateDevice challenge to Trezor.
    proof = device.authenticate(session, challenge)

    data = b"\x13AuthenticateDevice:" + compact_size(len(challenge)) + challenge
    check_signature_optiga(
        proof.optiga_signature, proof.optiga_certificates, session.model, data
    )


@pytest.mark.parametrize(
    "challenge",
    (
        b"",
        b"hello world",
        b"\x00" * 1024,
        bytes.fromhex(
            "21f3d40e63c304d0312f62eb824113efd72ba1ee02bef6777e7f8a7b6f67ba16"
        ),
    ),
)
@pytest.mark.models("core", skip=["safe3", "safe5"], reason="Not using Tropic")
def test_authenticate_device_tropic(session: Session, challenge: bytes) -> None:
    # NOTE Applications must generate a random challenge for each request.

    if not session.features.bootloader_locked:
        pytest.xfail("unlocked bootloader")

    # Issue an AuthenticateDevice challenge to Trezor.
    proof = device.authenticate(session, challenge)

    data = b"\x13AuthenticateDevice:" + compact_size(len(challenge)) + challenge
    check_signature_tropic(
        proof.tropic_signature,
        proof.tropic_certificates,
        session.model,
        data,
    )
