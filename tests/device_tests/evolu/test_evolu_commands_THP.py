import os

import pytest

from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import (
    EvoluDelegatedIdentityKey,
    EvoluGetDelegatedIdentityKey,
    ThpCredentialResponse,
)
from trezorlib.transport.thp import curve25519

# make -C core test_emu TESTOPTS="-k test_evolu_commands_THP.py"

pytestmark = pytest.mark.models("thp")

TEST_host_static_private_key = curve25519.get_private_key(os.urandom(32))
TEST_host_static_public_key = curve25519.get_public_key(TEST_host_static_private_key)


class ThpPairingResult:
    def __init__(self, session, credential):
        self.session: Session = session
        self.credential: ThpCredentialResponse = credential


def pair_and_get_credential(client: Client) -> ThpPairingResult:
    from trezorlib.messages import (
        ThpCredentialRequest,
        ThpCredentialResponse,
        ThpEndRequest,
        ThpEndResponse,
    )

    from ..thp.connect import prepare_protocol_for_pairing
    from ..thp.test_pairing import nfc_pairing

    protocol = prepare_protocol_for_pairing(client)
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


def test_evolu_get_delegated_identity_is_constant_ts7(client: Client):
    pairing_data = pair_and_get_credential(client)
    credential_data = pairing_data.credential
    session = pairing_data.session

    response = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credentials=credential_data.credential,
            host_static_public_key=TEST_host_static_public_key,
        ),
        expect=EvoluDelegatedIdentityKey,
    )

    private_key = response.private_key
    assert len(private_key) == 32

    response_2 = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credentials=credential_data.credential,
            host_static_public_key=TEST_host_static_public_key,
        ),
        expect=EvoluDelegatedIdentityKey,
    )
    assert response_2.private_key == private_key


def test_evolu_get_delegated_identity_test_vector_ts7(client: Client):
    # on emulator, the additional salt is all zeroes. So the delegated identity key is constant.

    pairing_data = pair_and_get_credential(client)
    credential_data = pairing_data.credential
    session = pairing_data.session

    response = session.call(
        EvoluGetDelegatedIdentityKey(
            thp_credentials=credential_data.credential,
            host_static_public_key=TEST_host_static_public_key,
        ),
        expect=EvoluDelegatedIdentityKey,
    )

    private_key = response.private_key
    assert private_key == bytes.fromhex(
        "0e71b5d486a6738f85db46d4dfc8446ccb4d9804aa48e7624620f7cea291f278"
    )
