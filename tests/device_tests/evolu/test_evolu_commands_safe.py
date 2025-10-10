import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

pytestmark = pytest.mark.models("safe")


@pytest.mark.protocol("protocol_v1")
def test_evolu_get_delegated_identity_is_constant(session: "Session"):
    private_key = evolu.get_delegated_identity_key(session)
    assert len(private_key) == 32

    private_key_2 = evolu.get_delegated_identity_key(session)
    assert private_key_2 == private_key


@pytest.mark.protocol("protocol_v1")
def test_evolu_get_delegated_identity_test_vector(session: "Session"):
    # on emulator, the master key is all zeroes. So the delegated identity key is constant.
    private_key = evolu.get_delegated_identity_key(session)
    assert private_key == bytes.fromhex(
        "c6389a1a662218ce2ff8db74dd2e2e428a23e9388ae3279466fedfcbd82efb34"
    )


def test_evolu_get_node(session: "Session"):
    proof = bytes.fromhex(
        "1f354fbb47b4679c1cb0c2c6b96a27f9a147c61ec5ef6f6c42491c839f4b7a95792d099be0f138274e5ef7896058b4de4f383f497792bb157b925e2644a79a0d84"
    )
    node = evolu.get_evolu_node(session, proof=proof)

    check_value = bytes.fromhex(
        "a81aaf51997b6ddfa33d11c038d6aba5f711754a2c823823ff8b777825cdbb32b0e71c301fa381c75081bd3bcc134b63306aa6fc9a9f52d835ad4df8cd507be6"
    )
    assert node == check_value


def test_evolu_get_node_invalid_proof(session: "Session"):
    proof = bytes.fromhex(
        "1f354fbb47b4679c1cb0c2c6b96a27f9a147c61ec5ef6f6c42491c839f4b7a95792d099be0f138274e5ef7896058b4de4f383f497792bb157b925e2644a79a0000"  # altered last 2 bytes
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.get_evolu_node(session, proof=proof)


def test_evolu_sign_request(session: "Session"):
    challenge = "1234"
    size = 10
    proposed_value = bytes.fromhex(
        "20dc125b51c2f596df4a9ae9ef816353dcdbf068b91ac687962742b8bd434276f60258c337e0d03211e599701a87cae8d8ac3258ce01bd484921743c2a5e99ec73"
    )
    response = evolu.evolu_sign_registration_request(
        session,
        challenge=bytes.fromhex(challenge),
        size=size,
        proof=proposed_value,
    )

    check_signature = bytes.fromhex(
        "30440220200c0fd62451a8285b9ebf091b72f5db32671220df51fd0ce280c9a9f0d77fb9022043c6031d9358be79ccc92744fb24522cae7d5ff0d146e1227e4f9adb3fd97e4c"
    )

    assert response.signature == check_signature


def test_evolu_sign_request_invalid_proof(session: "Session"):
    challenge = "1234"
    size = 10
    proposed_value = bytes.fromhex(
        "20dc125b51c2f596df4a9ae9ef816353dcdbf068b91ac687962742b8bd434276f60258c337e0d03211e599701a87cae8d8ac3258ce01bd484921743c2a5e990000"  # altered last 2 bytes
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid proof",
    ):
        evolu.evolu_sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


def test_evolu_sign_request_challenge_too_long(session: "Session"):
    challenge = "01" * 300  # 300 bytes, max is 255
    size = 10
    proposed_value = bytes.fromhex(
        "1fd0b4cd0a04806eaa74ae59cc2f5a740680fc784b877deff6ffa6b9eda7d5a7d4207958c48e679b18c64d0e7fcd0e5be25eb27bcf186fbf9531eb20bce7234a23"
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid challenge length",
    ):
        evolu.evolu_sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


def test_evolu_sign_request_challenge_too_short(session: "Session"):
    challenge = ""  # 0 bytes, min is 1
    size = 10
    proposed_value = bytes.fromhex(
        "1fa386d20efb38dbb3f7ae0509651fa36c8128324ef89fa1cfd104e10dced08c594f0e8f0a525a839b4fbfaa92b8c2b51163cef593f5c14fc9f1c8c48d1192270d"
    )

    with pytest.raises(
        TrezorFailure,
        match="Invalid challenge length",
    ):
        evolu.evolu_sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


def test_evolu_sign_request_size_too_small(session: "Session"):
    challenge = "1234"
    size = -10
    proposed_value = bytes.fromhex(
        "1fa386d20efb38dbb3f7ae0509651fa36c8128324ef89fa1cfd104e10dced08c594f0e8f0a525a839b4fbfaa92b8c2b51163cef593f5c14fc9f1c8c48d1192270d"
    )

    with pytest.raises(
        ValueError,
        match=f"Value {size} in field size_to_acquire does not fit into uint32",
    ):
        evolu.evolu_sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


def test_evolu_sign_request_size_too_large(session: "Session"):
    challenge = "1234"
    size = 0xFFFFFFFF + 1
    proposed_value = bytes.fromhex(
        "1fa386d20efb38dbb3f7ae0509651fa36c8128324ef89fa1cfd104e10dced08c594f0e8f0a525a839b4fbfaa92b8c2b51163cef593f5c14fc9f1c8c48d1192270d"
    )

    with pytest.raises(
        ValueError,
        match=f"Value {size} in field size_to_acquire does not fit into uint32",
    ):
        evolu.evolu_sign_registration_request(
            session,
            challenge=bytes.fromhex(challenge),
            size=size,
            proof=proposed_value,
        )


def test_evolu_sign_request_data_higher_bound(session: "Session"):
    challenge = "12" * 255
    size = 0xFFFFFFFF
    proposed_value = bytes.fromhex(
        "1f01b8fbc9f741d7cb418b3bc0144e99e125c5a2d2f0a792a883f7924cbb1abc386cf6053569449fd6ba6204a34d5757ea6d5b26f9e77c876fb6294f268c227f17"
    )

    response = evolu.evolu_sign_registration_request(
        session,
        challenge=bytes.fromhex(challenge),
        size=size,
        proof=proposed_value,
    )
    check_signature = bytes.fromhex(
        "304502210095a5080800736a89c3583a0c64fad78e1811c43bf4fc03114a15fedee0f848d7022044c61018ad24fd1e39835ad11b3a81a17c15bd0f9bc48cf1e41b8a6990c0aea9"
    )

    print(response.signature.hex())

    assert response.signature == check_signature
