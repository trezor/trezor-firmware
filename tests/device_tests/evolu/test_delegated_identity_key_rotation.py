import pytest

from trezorlib import debuglink, device, evolu
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.exceptions import TrezorFailure

from .common import get_delegated_identity_key

pytestmark = [
    pytest.mark.models("core"),
    # we need to start each test from the same state - wiped and freshly set seed
    pytest.mark.setup_client(passphrase=False),
]


def test_first_rotation_index_is_None(client: Client):
    response_none = evolu.index_management(client.get_session())
    assert response_none.rotation_index is None

    delegated_identity_key = get_delegated_identity_key(client)
    assert delegated_identity_key.rotation_index is None

    with pytest.raises(
        TrezorFailure,
        match=r"DataError: Requested rotation index \(1\) is higher than the current rotation index \(None\)",
    ):
        get_delegated_identity_key(client, rotation_index=1)


def test_delegated_identity_key_rotation_index_increment(client: Client):
    response = evolu.index_management(client.get_session(), rotation_index=2)
    assert response.rotation_index == 2

    delegated_identity_key_0 = get_delegated_identity_key(client, rotation_index=0)
    delegated_identity_key_1 = get_delegated_identity_key(client, rotation_index=1)
    delegated_identity_key_2 = get_delegated_identity_key(client, rotation_index=2)
    delegated_identity_key_last = get_delegated_identity_key(client)

    assert delegated_identity_key_0.rotation_index == 0
    assert delegated_identity_key_1.rotation_index == 1
    assert delegated_identity_key_2.rotation_index == 2
    assert delegated_identity_key_last.rotation_index == 2

    assert delegated_identity_key_0.private_key != delegated_identity_key_1.private_key
    assert delegated_identity_key_1.private_key != delegated_identity_key_2.private_key
    assert delegated_identity_key_0.private_key != delegated_identity_key_2.private_key
    assert (
        delegated_identity_key_last.private_key == delegated_identity_key_2.private_key
    )

    with pytest.raises(
        TrezorFailure,
        match=r"DataError: Requested rotation index \(3\) is higher than the current rotation index \(2\)",
    ):
        get_delegated_identity_key(client, rotation_index=3)


def test_delegated_identity_key_rotation(client: Client):
    delegated_identity_key_0 = get_delegated_identity_key(client)
    assert delegated_identity_key_0.rotation_index is None

    delegated_identity_key_1 = evolu.get_delegated_identity_key(
        client.get_session(), rotate=True
    )
    assert delegated_identity_key_1.rotation_index == 1
    assert delegated_identity_key_0.private_key != delegated_identity_key_1.private_key

    delegated_identity_key_2 = evolu.get_delegated_identity_key(
        client.get_session(), rotate=True
    )
    assert delegated_identity_key_2.rotation_index == 2
    assert delegated_identity_key_1.private_key != delegated_identity_key_2.private_key
    assert delegated_identity_key_0.private_key != delegated_identity_key_2.private_key


def test_delegated_identity_key_rotation_max_index(client: Client):
    # set rotation index to the maximum allowed value
    evolu.index_management(client.get_session(), rotation_index=(1 << 16) - 1)

    with pytest.raises(
        TrezorFailure,
        match="DataError: Maximum rotation index reached",
    ):
        evolu.get_delegated_identity_key(client.get_session(), rotate=True)


def test_rotate_affects_index_management(client: Client):
    evolu.get_delegated_identity_key(client.get_session(), rotate=True)

    with pytest.raises(
        TrezorFailure,
        match=r"FirmwareError: Rotation index already set.",
    ):
        evolu.index_management(client.get_session(), rotation_index=50)

    response = evolu.index_management(client.get_session())
    assert response.rotation_index == 1


def test_index_management_cannot_overwrite_existing_index(client: Client):
    response = evolu.index_management(client.get_session(), rotation_index=10)
    assert response.rotation_index == 10

    with pytest.raises(
        TrezorFailure,
        match=r"FirmwareError: Rotation index already set.",
    ):
        evolu.index_management(client.get_session(), rotation_index=5)

    with pytest.raises(
        TrezorFailure,
        match=r"FirmwareError: Rotation index already set.",
    ):
        evolu.index_management(client.get_session(), rotation_index=15)

    key = get_delegated_identity_key(client)
    assert key.rotation_index == 10


def test_rotation_index_wiped_on_device_wipe(client: Client):
    evolu.index_management(client.get_session(), rotation_index=0)
    key_before_wipe_0 = get_delegated_identity_key(client)
    assert key_before_wipe_0.rotation_index == 0
    evolu.get_delegated_identity_key(client.get_session(), rotate=True)

    key_before_wipe_1 = get_delegated_identity_key(client)
    assert key_before_wipe_1.rotation_index == 1

    session = client.get_session()
    device.wipe(session)
    session = client.get_seedless_session()
    debuglink.load_device(
        session,
        mnemonic=" ".join(["all"] * 12),
        pin=None,
        passphrase_protection=False,
        label="test",
    )

    key_after_wipe = get_delegated_identity_key(client)
    assert key_after_wipe.rotation_index is None
    assert key_before_wipe_1.private_key != key_after_wipe.private_key
    assert key_before_wipe_0.private_key == key_after_wipe.private_key


def test_index_management_getter(client: Client):
    response = evolu.index_management(client.get_session(), rotation_index=None)
    assert response.rotation_index is None

    evolu.index_management(client.get_session(), rotation_index=5)

    response = evolu.index_management(client.get_session(), rotation_index=None)
    assert response.rotation_index == 5


def test_explicit_index_zero_on_uninitialized_device(client: Client):
    # Ensure device is uninitialized
    response = evolu.index_management(client.get_session())
    assert response.rotation_index is None

    # Even though state is None, asking for explicit 0 should work
    # because the firmware logic treats (None -> 0)
    key_explicit = get_delegated_identity_key(client, rotation_index=0)

    # The default fetch uses 0 for derivation but returns rotation_index=None in metadata
    key_default = get_delegated_identity_key(client)

    # Keys should be identical (both derived from index 0)
    assert key_explicit.private_key == key_default.private_key

    # But metadata differs: explicit request gets explicit index back
    assert key_explicit.rotation_index == 0
    assert key_default.rotation_index is None
