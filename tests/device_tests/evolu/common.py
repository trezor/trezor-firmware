import os
from hashlib import sha256
from typing import List

from ecdsa import NIST256p, SigningKey

from trezorlib import evolu
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import (
    ThpCredentialRequest,
    ThpCredentialResponse,
    ThpEndRequest,
    ThpEndResponse,
)
from trezorlib.transport.thp import curve25519

from ...common import compact_size
from ..thp.connect import prepare_protocol_for_pairing
from ..thp.test_pairing import nfc_pairing

TEST_randomness = os.urandom(32)
TEST_host_static_private_key = curve25519.get_private_key(TEST_randomness)
TEST_host_static_public_key = curve25519.get_public_key(TEST_host_static_private_key)


def get_proof(client: Client, header: bytes, arguments: List[bytes]) -> bytes:
    private_key = get_delegated_identity_key(client)
    signing_key = SigningKey.from_string(private_key, curve=NIST256p)

    ctx = sha256()
    ctx.update(compact_size(len(header)))
    ctx.update(header)
    for arg in arguments:
        ctx.update(compact_size(len(arg)))
        ctx.update(arg)
    return signing_key.sign_digest(ctx.digest())


def get_invalid_proof(client: Client, header: bytes, arguments: List[bytes]) -> bytes:
    valid_proof = get_proof(client, header, arguments)
    # tamper with the proof to make it invalid
    invalid_proof = (
        valid_proof[:-2]
        + bytes([valid_proof[-2] ^ 0xFF])
        + bytes([valid_proof[-1] ^ 0xFF])
    )
    return invalid_proof


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


def pair_and_get_invalid_credential(client: Client) -> ThpPairingResult:
    pairing_result = pair_and_get_credential(client)
    credential = pairing_result.credential.credential

    # Corrupt the credential to make it invalid
    invalid_credential = (
        credential[:-2]
        + bytes([credential[-2] ^ 0xFF])
        + bytes([credential[-1] ^ 0xFF])
    )
    pairing_result.credential.credential = invalid_credential
    return pairing_result


def get_delegated_identity_key(client: Client) -> bytes:
    if client.protocol_version == 2:
        pairing_data = pair_and_get_credential(client)
        return evolu.get_delegated_identity_key(
            client.get_session(),
            thp_credential=pairing_data.credential.credential,
        )
    elif client.protocol_version == 1:
        return evolu.get_delegated_identity_key(client.get_session())
    else:
        raise ValueError("Unsupported protocol version")
