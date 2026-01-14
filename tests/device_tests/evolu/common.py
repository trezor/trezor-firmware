import os
from hashlib import sha256
from typing import List

from ecdsa import NIST256p, SigningKey

from trezorlib import evolu
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.messages import ThpCredentialResponse
from trezorlib.thp import curve25519

from ...common import compact_size

TEST_host_static_private_key = curve25519.get_private_key(os.urandom(32))
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
    from ..thp.connect import nfc_pairing, prepare_channel_for_pairing

    prepare_channel_for_pairing(
        client, host_static_privkey=TEST_host_static_private_key
    )
    nfc_pairing(client)
    credential = client.pairing.request_credential(autoconnect=False)
    client.pairing.finish()

    return ThpPairingResult(client.get_session(), credential)


def get_delegated_identity_key(client: Client) -> bytes:
    if client.is_thp():
        pairing_data = pair_and_get_credential(client)
        return evolu.get_delegated_identity_key(
            client.get_session(),
            thp_credential=pairing_data.credential.credential,
            host_static_public_key=TEST_host_static_public_key,
        )
    elif client.is_protocol_v1():
        return evolu.get_delegated_identity_key(client.get_session())
    else:
        raise ValueError("Unsupported protocol version")
