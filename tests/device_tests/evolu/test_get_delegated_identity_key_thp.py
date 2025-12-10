import pytest

from trezorlib.debuglink import TrezorTestContext
from trezorlib.messages import EvoluDelegatedIdentityKey, EvoluGetDelegatedIdentityKey

from ..thp.connect import nfc_pairing, prepare_channel_for_pairing

pytestmark = [pytest.mark.protocol("thp"), pytest.mark.models("core")]


def test_evolu_get_delegated_identity_is_constant(test_ctx: TrezorTestContext):
    prepare_channel_for_pairing(test_ctx)
    nfc_pairing(test_ctx)
    credential_data = test_ctx.client.pairing.request_credential()
    credential = credential_data.credential
    host_static_pubkey = test_ctx.channel.get_host_static_pubkey()
    session = test_ctx.client.get_session()

    response = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credential=credential,
            host_static_public_key=host_static_pubkey,
        ),
        expect=EvoluDelegatedIdentityKey,
    )

    private_key = response.private_key
    assert len(private_key) == 32

    response_2 = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credential=credential,
            host_static_public_key=host_static_pubkey,
        ),
        expect=EvoluDelegatedIdentityKey,
    )
    assert response_2.private_key == private_key


def test_evolu_get_delegated_identity_test_vector(test_ctx: TrezorTestContext):
    # on emulator, the master key is all zeroes. So the delegated identity key is constant.
    prepare_channel_for_pairing(test_ctx)
    nfc_pairing(test_ctx)
    credential_data = test_ctx.client.pairing.request_credential()
    credential = credential_data.credential
    host_static_pubkey = test_ctx.channel.get_host_static_pubkey()
    session = test_ctx.client.get_session()

    response = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credential=credential,
            host_static_public_key=host_static_pubkey,
        ),
        expect=EvoluDelegatedIdentityKey,
    )

    private_key = response.private_key
    assert private_key == bytes.fromhex(
        "10e39ed3a40dd63a47a14608d4bccd4501170cf9f2188223208084d39c37b369"
    )
