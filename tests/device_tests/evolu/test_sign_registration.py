import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

pytestmark = pytest.mark.models("core")


@pytest.mark.models("t2t1")
def test_evolu_sign_request_t2t1(session: Session):
    challenge = "1234"
    size = 10
    proposed_value = bytes.fromhex(
        "1b161be2bfc622b4ffd9943138ab5931e77b4c6835e29b1ac25221c74492495a912c00f488fd5f95b43085f721f36574813785c011c60cf81877ccd057df6bed0c"
    )

    with pytest.raises(
        TrezorFailure,
        match="Optiga is not available",
    ):
        evolu.sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request(session: Session):
    challenge = "1234"
    size = 10
    proposed_value = bytes.fromhex(
        "1fb4ca7b8d956cc50ac652e383691af8e59b200adedde3a898b86795fd94d49241559a1699de1110617a91c44c70c4b9509fdb36f5057a52c0ef28fce7afa10734"
    )
    response = evolu.sign_registration_request(
        session,
        challenge=bytes.fromhex(challenge),
        size=size,
        proof=proposed_value,
    )

    check_signature = bytes.fromhex(
        "30440220148c0a0026828532e5a2e7ce5cf2dcd2491e7eea5f5c6eafd49779d1502c5ba102204b1ca171045969e38ac815de09462d6c5b496d04851266fe71abcf55b9aee672"
    )

    assert response.signature == check_signature


@pytest.mark.models("safe")
def test_evolu_sign_request_invalid_proof(session: Session):
    challenge = "1234"
    size = 10
    proposed_value = bytes.fromhex(
        "20dc125b51c2f596df4a9ae9ef816353dcdbf068b91ac687962742b8bd434276f60258c337e0d03211e599701a87cae8d8ac3258ce01bd484921743c2a5e990000"  # altered last 2 bytes
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_challenge_too_long(session: Session):
    challenge = "01" * 300  # 300 bytes, max is 255
    size = 10
    proposed_value = bytes.fromhex(
        "1fd0b4cd0a04806eaa74ae59cc2f5a740680fc784b877deff6ffa6b9eda7d5a7d4207958c48e679b18c64d0e7fcd0e5be25eb27bcf186fbf9531eb20bce7234a23"
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid challenge length",
    ):
        evolu.sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_challenge_too_short(session: Session):
    challenge = ""  # 0 bytes, min is 1
    size = 10
    proposed_value = bytes.fromhex(
        "1fa386d20efb38dbb3f7ae0509651fa36c8128324ef89fa1cfd104e10dced08c594f0e8f0a525a839b4fbfaa92b8c2b51163cef593f5c14fc9f1c8c48d1192270d"
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid challenge length",
    ):
        evolu.sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_size_too_small(session: Session):
    challenge = "1234"
    size = -10
    proposed_value = bytes.fromhex(
        "1fa386d20efb38dbb3f7ae0509651fa36c8128324ef89fa1cfd104e10dced08c594f0e8f0a525a839b4fbfaa92b8c2b51163cef593f5c14fc9f1c8c48d1192270d"
    )

    with pytest.raises(
        ValueError,
        match=f"Value {size} in field size_to_acquire does not fit into uint32",
    ):
        evolu.sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_size_too_large(session: Session):
    challenge = "1234"
    size = 0xFFFFFFFF + 1
    proposed_value = bytes.fromhex(
        "1fa386d20efb38dbb3f7ae0509651fa36c8128324ef89fa1cfd104e10dced08c594f0e8f0a525a839b4fbfaa92b8c2b51163cef593f5c14fc9f1c8c48d1192270d"
    )

    with pytest.raises(
        ValueError,
        match=f"Value {size} in field size_to_acquire does not fit into uint32",
    ):
        evolu.sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


@pytest.mark.models("safe")
def test_evolu_sign_request_data_higher_bound(session: Session):
    challenge = "12" * 255
    size = 0xFFFFFFFF
    proposed_value = bytes.fromhex(
        "1f1971f6ce302562e737520c0de2338cdaaac4e676fa02ff857b3b6081ebde794545f25905128ae9c9e7861e2358fe2e94821dd9e902564ec11478e5c6b60527c8"
    )

    response = evolu.sign_registration_request(
        session,
        challenge=bytes.fromhex(challenge),
        size=size,
        proof=proposed_value,
    )
    check_signature = bytes.fromhex(
        "304402202fedb9dee42c4cb19c27daab8c5f8cbfb74047fa65a5521e1f410a14cb0ab41502202d76b31fe1c97e4577191825bc39e0b01a3bafcba3615130175cbe11d5714832"
    )
    assert response.signature == check_signature
