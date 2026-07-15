import pytest
from cryptography import x509

from trezorlib import device, exceptions, messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import compact_size

from .certificate import (
    check_signature_mcu,
    check_signature_optiga,
    check_signature_tropic,
)

# The tests below require Optiga (and some require Tropic)
pytestmark = pytest.mark.models("safe")


@pytest.fixture(
    scope="module",
    params=[
        pytest.param(b"", id="empty"),
        pytest.param(b"hello world", id="hello_world"),
        pytest.param(b"\x00" * 1024, id="1kB_zeroes"),
        pytest.param(
            bytes.fromhex(
                "21f3d40e63c304d0312f62eb824113efd72ba1ee02bef6777e7f8a7b6f67ba16"
            ),
            id="32B_digest",
        ),
    ],
)
def challenge(request: pytest.FixtureRequest) -> bytes:
    return request.param


@pytest.fixture(scope="module", params=[0, 16, 1024])
def chunk_size(request: pytest.FixtureRequest) -> int:
    return request.param


def test_authenticate_device_optiga(
    session: Session, challenge: bytes, chunk_size: int
) -> None:
    # NOTE Applications must generate a random challenge for each request.

    if not session.features.bootloader_locked:
        pytest.xfail("unlocked bootloader")

    # Issue an AuthenticateDevice challenge to Trezor.
    proof = device.authenticate(session, challenge, chunk_size)
    if chunk_size == 0:
        # MCU attestation is sent only when streaming is supported.
        assert proof.mcu_signature is None
        assert proof.mcu_certificates == []

    data = b"\x13AuthenticateDevice:" + compact_size(len(challenge)) + challenge
    check_signature_optiga(
        proof.optiga_signature, proof.optiga_certificates, session.model, data
    )


@pytest.mark.models(skip=["safe3", "safe5"])
def test_authenticate_device_mcu(
    session: Session, challenge: bytes, chunk_size: int
) -> None:
    # NOTE Applications must generate a random challenge for each request.

    if not session.features.bootloader_locked:
        pytest.xfail("unlocked bootloader")

    if chunk_size == 0:
        # MCU attestation is sent only when streaming is supported.
        pytest.skip("MCU attestation requires streaming (chunk_size > 0)")

    proof = device.authenticate(session, challenge, chunk_size)
    assert proof.mcu_signature is not None
    assert len(proof.mcu_certificates) >= 1

    data = b"\x13AuthenticateDevice:" + compact_size(len(challenge)) + challenge
    check_signature_mcu(
        proof.mcu_signature, proof.mcu_certificates, session.model, data
    )


@pytest.mark.models(skip=["safe3", "safe5"], reason="Not using Tropic")
def test_authenticate_device_tropic(
    session: Session, challenge: bytes, chunk_size: int
) -> None:
    # NOTE Applications must generate a random challenge for each request.

    if not session.features.bootloader_locked:
        pytest.xfail("unlocked bootloader")

    # Issue an AuthenticateDevice challenge to Trezor.
    proof = device.authenticate(session, challenge, chunk_size)
    if chunk_size == 0:
        # MCU attestation is sent only when streaming is supported.
        assert proof.mcu_signature is None
        assert proof.mcu_certificates == []

    data = b"\x13AuthenticateDevice:" + compact_size(len(challenge)) + challenge
    check_signature_tropic(
        proof.tropic_signature,
        proof.tropic_certificates,
        session.model,
        data,
    )


@pytest.fixture(scope="function")
def proof_sizes(session: Session) -> messages.AuthenticityProofSizes:
    """Fetch AuthenticityProof sizes, for testing invalid subsequent requests."""
    if not session.features.bootloader_locked:
        pytest.xfail("unlocked bootloader")

    # Issue an AuthenticateDevice challenge to Trezor.
    return session.call(
        messages.AuthenticateDevice(challenge=b"", stream=True),
        expect=messages.AuthenticityProofSizes,
    )


@pytest.mark.models(["safe3", "safe5"], reason="No tropic signature")
def test_authenticate_device_no_signature(
    session: Session, proof_sizes: messages.AuthenticityProofSizes
) -> None:
    assert proof_sizes.tropic_signature is None
    assert proof_sizes.tropic_certificates == []

    # fetch missing signature (no Tropic on this model)
    with pytest.raises(exceptions.TrezorFailure, match="DataError: No signature"):
        session.call(
            messages.GetAuthenticityProofChunk(
                proof_type=messages.AuthenticityProofType.TROPIC,
                index=None,
                offset=0,
                size=0,
            )
        )


def test_authenticate_device_no_certificate(
    session: Session, proof_sizes: messages.AuthenticityProofSizes
) -> None:
    # use wrong index when requesting a certificate
    with pytest.raises(exceptions.TrezorFailure, match="DataError: No certificate"):
        session.call(
            messages.GetAuthenticityProofChunk(
                proof_type=messages.AuthenticityProofType.OPTIGA,
                index=len(proof_sizes.optiga_certificates),
                offset=0,
                size=0,
            )
        )


def test_authenticate_device_invalid_range_size(
    session: Session, proof_sizes: messages.AuthenticityProofSizes
) -> None:
    # use wrong chunk range size
    with pytest.raises(
        exceptions.TrezorFailure, match="DataError: Invalid chunk range"
    ):
        session.call(
            messages.GetAuthenticityProofChunk(
                proof_type=messages.AuthenticityProofType.OPTIGA,
                index=None,
                offset=0,
                size=proof_sizes.optiga_signature + 1,
            )
        )


def test_authenticate_device_invalid_range_offset(
    session: Session, proof_sizes: messages.AuthenticityProofSizes
) -> None:
    # use wrong chunk range offset
    with pytest.raises(
        exceptions.TrezorFailure, match="DataError: Invalid chunk range"
    ):
        session.call(
            messages.GetAuthenticityProofChunk(
                proof_type=messages.AuthenticityProofType.OPTIGA,
                index=None,
                offset=proof_sizes.optiga_signature + 1,
                size=0,
            )
        )


@pytest.mark.models(skip=["safe3", "safe5"], reason="Not using Tropic")
def test_certificate_subject_serial_numbers_match(
    session: Session,
) -> None:
    if not session.features.bootloader_locked:
        pytest.xfail("unlocked bootloader")

    proof = device.authenticate(session, b"")

    def serial_number(cert_der: bytes) -> str:
        cert = x509.load_der_x509_certificate(cert_der)
        attrs = cert.subject.get_attributes_for_oid(x509.oid.NameOID.SERIAL_NUMBER)
        assert attrs
        return attrs[0].value

    optiga_sn = serial_number(proof.optiga_certificates[0])
    tropic_sn = serial_number(proof.tropic_certificates[0])
    mcu_sn = serial_number(proof.mcu_certificates[0])

    assert optiga_sn == tropic_sn == mcu_sn


def test_authenticate_device_unexpected(
    session: Session, proof_sizes: messages.AuthenticityProofSizes
) -> None:
    session.client.ping("Should stop AuthenticityProof streaming")

    with pytest.raises(
        exceptions.TrezorFailure, match="UnexpectedMessage: Unexpected message"
    ):
        session.call(
            messages.GetAuthenticityProofChunk(
                proof_type=None,
                offset=0,
                size=0,
            )
        )
