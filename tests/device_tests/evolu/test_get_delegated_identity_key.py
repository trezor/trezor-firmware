import pytest

from trezorlib import models
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import EvoluDelegatedIdentityKey, EvoluGetDelegatedIdentityKey

from .common import (
    get_delegated_identity_key,
    pair_and_get_credential,
    pair_and_get_invalid_credential,
)

pytestmark = [pytest.mark.models("core")]


def test_evolu_get_delegated_identity_is_constant(client: Client):
    private_key = get_delegated_identity_key(client).private_key
    assert len(private_key) == 32

    private_key_2 = get_delegated_identity_key(client).private_key
    assert private_key_2 == private_key


def test_evolu_get_delegated_identity_test_vector(client: Client):
    # on emulator, the master key is hardcoded. So the delegated identity key is constant.
    if not client.is_emulator:
        pytest.skip("Only for emulator")

    if client.model in (models.T3W1, models.T3T2):
        # models with an unprivileged master key slot derive the key from the
        # hardcoded emulator secret, see core/embed/sec/secret/unix/secret.c
        expected = "99c0adb27ce114742e04ead75236cbb5ebd91e6a0954c1df12616372d7269929"
    else:
        # the remaining models derive the key from an all-zero master key
        expected = "10e39ed3a40dd63a47a14608d4bccd4501170cf9f2188223208084d39c37b369"

    private_key = get_delegated_identity_key(client).private_key
    assert private_key == bytes.fromhex(expected)


@pytest.mark.protocol("protocol_v2")
def test_evolu_get_delegated_identity_invalid_credential(client: Client):
    pairing_data = pair_and_get_invalid_credential(client)
    credential_data = pairing_data.credential
    session = pairing_data.session

    with pytest.raises(TrezorFailure, match="DataError: Invalid credential"):
        session.call(
            EvoluGetDelegatedIdentityKey(
                thp_credential=credential_data.credential,
            ),
            expect=EvoluDelegatedIdentityKey,
        )


@pytest.mark.protocol("protocol_v2")
def test_evolu_get_delegated_identity_missing_credential(client: Client):
    pairing_data = pair_and_get_credential(client)
    session = pairing_data.session

    with pytest.raises(
        TrezorFailure,
        match="DataError: THP credential must be provided when THP is enabled",
    ):
        session.call(
            EvoluGetDelegatedIdentityKey(
                thp_credential=None,  # Missing credential
            ),
            expect=EvoluDelegatedIdentityKey,
        )
