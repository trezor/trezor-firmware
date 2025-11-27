import os
from hashlib import sha256
from typing import List

from ecdsa import NIST256p, SigningKey

from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import ThpCredentialResponse
from trezorlib.transport.thp import curve25519
from trezorlib import evolu


from ...common import compact_size

TEST_host_static_private_key = curve25519.get_private_key(os.urandom(32))
TEST_host_static_public_key = curve25519.get_public_key(TEST_host_static_private_key)


def sign_proof(private_key: bytes, header: bytes, arguments: List[bytes]) -> bytes:
    signing_key = SigningKey.from_string(private_key, curve=NIST256p)

    ctx = sha256()
    ctx.update(compact_size(len(header)))
    ctx.update(header)
    for arg in arguments:
        ctx.update(compact_size(len(arg)))
        ctx.update(arg)
    return signing_key.sign_digest(ctx.digest())


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

def get_delegated_identity_key(client: Client) -> bytes:
    if client.protocol_version == 2:
        pairing_data = pair_and_get_credential(client)
        return evolu.get_delegated_identity_key(
            client.get_session(),
            thp_credential=pairing_data.credential.credential,
            host_static_public_key=TEST_host_static_public_key,
        )
    elif client.protocol_version == 1:
        return evolu.get_delegated_identity_key(client.get_session())
    else:
        raise ValueError("Unsupported protocol version")