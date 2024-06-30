from typing import TYPE_CHECKING

from trezor import protobuf
from trezor.crypto import hmac
from trezor.messages import (
    ThpAuthenticatedCredentialData,
    ThpCredentialMetadata,
    ThpPairingCredential,
)
from trezor.wire import wrap_protobuf_load

if TYPE_CHECKING:
    from apps.common.paths import Slip21Path


def derive_cred_auth_key() -> bytes:
    """
    Derive current credential authentication mac-ing key from device secret.
    """
    from storage.device import get_cred_auth_key_counter, get_device_secret

    from apps.common.seed import Slip21Node

    # Derive the key using SLIP-21 https://github.com/satoshilabs/slips/blob/master/slip-0021.md,
    # the derivation path is m/"Credential authentication key"/(counter 4-byte BE)

    thp_secret = get_device_secret()
    label = b"Credential authentication key"
    counter = get_cred_auth_key_counter()
    path: Slip21Path = [label, counter]

    symmetric_key_node: Slip21Node = Slip21Node(thp_secret)
    symmetric_key_node.derive_path(path)
    cred_auth_key = symmetric_key_node.key()

    return cred_auth_key


def invalidate_cred_auth_key() -> None:
    from storage.device import increment_cred_auth_key_counter

    increment_cred_auth_key_counter()


def issue_credential(
    host_static_pubkey: bytes,
    credential_metadata: ThpCredentialMetadata,
) -> bytes:
    """
    Issue a pairing credential binded to the provided host static public key
    and credential metadata.
    """
    cred_auth_key = derive_cred_auth_key()
    proto_msg = ThpAuthenticatedCredentialData(
        host_static_pubkey=host_static_pubkey,
        cred_metadata=credential_metadata,
    )
    authenticated_credential_data = _encode_message_into_new_buffer(proto_msg)
    mac = hmac(hmac.SHA256, cred_auth_key, authenticated_credential_data).digest()

    proto_msg = ThpPairingCredential(cred_metadata=credential_metadata, mac=mac)
    credential_raw = _encode_message_into_new_buffer(proto_msg)
    return credential_raw


def validate_credential(
    encoded_pairing_credential_message: bytes,
    host_static_pubkey: bytes,
) -> bool:
    """
    Validate a pairing credential binded to the provided host static public key.
    """
    cred_auth_key = derive_cred_auth_key()
    expected_type = protobuf.type_for_name("ThpPairingCredential")
    credential = wrap_protobuf_load(encoded_pairing_credential_message, expected_type)
    assert ThpPairingCredential.is_type_of(credential)
    proto_msg = ThpAuthenticatedCredentialData(
        host_static_pubkey=host_static_pubkey,
        cred_metadata=credential.cred_metadata,
    )
    authenticated_credential_data = _encode_message_into_new_buffer(proto_msg)
    mac = hmac(hmac.SHA256, cred_auth_key, authenticated_credential_data).digest()
    return mac == credential.mac


def _encode_message_into_new_buffer(msg: protobuf.MessageType) -> bytes:
    msg_len = protobuf.encoded_length(msg)
    new_buffer = bytearray(msg_len)
    protobuf.encode(new_buffer, msg)
    return new_buffer
