import pytest

from trezorlib.debuglink import TrezorClientDebugLink as Client

from .common import get_delegated_identity_key

pytestmark = [pytest.mark.models("core")]


def test_evolu_get_delegated_identity_is_constant(client: Client):
    private_key = get_delegated_identity_key(client)
    assert len(private_key) == 32

    private_key_2 = get_delegated_identity_key(client)
    assert private_key_2 == private_key


def test_evolu_get_delegated_identity_test_vector(client: Client):
    # on emulator, the master key is all zeroes. So the delegated identity key is constant.
    if client.get_session().features.fw_vendor != "EMULATOR":
        pytest.skip("Only for emulator")

    private_key = get_delegated_identity_key(client)
    # hardcoded expected value for the emulator with zeroed master key
    assert private_key == bytes.fromhex(
        "10e39ed3a40dd63a47a14608d4bccd4501170cf9f2188223208084d39c37b369"
    )
