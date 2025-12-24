import os

import pytest

from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import (
    EvoluDelegatedIdentityKey,
    EvoluGetDelegatedIdentityKey,
    ThpCredentialRequest,
    ThpCredentialResponse,
    ThpEndRequest,
    ThpEndResponse,
)
from trezorlib.transport.thp import curve25519

from ..thp.connect import prepare_protocol_for_pairing
from ..thp.test_pairing import nfc_pairing

pytestmark = [pytest.mark.protocol("protocol_v2"), pytest.mark.models("core")]

TEST_randomness = os.urandom(32)
TEST_host_static_private_key = curve25519.get_private_key(TEST_randomness)
TEST_host_static_public_key = curve25519.get_public_key(TEST_host_static_private_key)


class ThpPairingResult:
    def __init__(self, session, credential):
        self.session: Session = session
        self.credential: ThpCredentialResponse = credential


def pair_and_get_credential(client: Client) -> ThpPairingResult:
    protocol = prepare_protocol_for_pairing(client, TEST_randomness)
    nfc_pairing(client, protocol)
    protocol._send_message(
        ThpCredentialRequest(
            host_static_public_key=TEST_host_static_public_key,
            autoconnect=False,
        )
    )
    credential_response = protocol._read_message(ThpCredentialResponse)

    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)
    protocol._is_paired = True

    client.protocol = protocol
    session = client.get_session()
    return ThpPairingResult(session, credential_response)


def test_evolu_get_delegated_identity_is_constant(client: Client):
    pairing_data = pair_and_get_credential(client)
    credential_data = pairing_data.credential
    session = pairing_data.session

    response = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credential=credential_data.credential,
        ),
        expect=EvoluDelegatedIdentityKey,
    )

    private_key = response.private_key
    assert len(private_key) == 32

    response_2 = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credential=credential_data.credential,
        ),
        expect=EvoluDelegatedIdentityKey,
    )
    assert response_2.private_key == private_key


def test_evolu_get_delegated_identity_test_vector(client: Client):
    # on emulator, the master key is all zeroes. So the delegated identity key is constant.

    pairing_data = pair_and_get_credential(client)
    credential_data = pairing_data.credential
    session = pairing_data.session

    response = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credential=credential_data.credential,
        ),
        expect=EvoluDelegatedIdentityKey,
    )

    private_key = response.private_key
    assert private_key == bytes.fromhex(
        "10e39ed3a40dd63a47a14608d4bccd4501170cf9f2188223208084d39c37b369"
    )
