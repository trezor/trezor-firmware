import pytest

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session

pytestmark = [pytest.mark.models("core"), pytest.mark.protocol("protocol_v1")]


def test_evolu_get_delegated_identity_is_constant(session: Session):
    private_key = evolu.get_delegated_identity_key(session, 0)
    assert len(private_key) == 32

    private_key_2 = evolu.get_delegated_identity_key(session, 0)
    assert private_key_2 == private_key


def test_evolu_get_delegated_identity_test_vector(session: Session):
    # on emulator, the master key is all zeroes. So the delegated identity key is constant.
    private_key = evolu.get_delegated_identity_key(session, 0)
    assert private_key == bytes.fromhex(
        "10e39ed3a40dd63a47a14608d4bccd4501170cf9f2188223208084d39c37b369"
    )


def test_evolu_get_delegated_identity_test_vector_index_1(session: Session):
    # on emulator, the master key is all zeroes. So the delegated identity key is constant.
    private_key = evolu.get_delegated_identity_key(session, 1)
    assert private_key == bytes.fromhex(
        "89ebc6011393c53b55bd416d8bb130e5b881c164ea9950a33d9718abd2eda9e7"
    )
