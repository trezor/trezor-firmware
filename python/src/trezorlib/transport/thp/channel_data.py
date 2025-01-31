from __future__ import annotations

from binascii import hexlify


class ChannelData:

    def __init__(
        self,
        protocol_version_major: int,
        protocol_version_minor: int,
        transport_path: str,
        channel_id: int,
        key_request: bytes,
        key_response: bytes,
        nonce_request: int,
        nonce_response: int,
        sync_bit_send: int,
        sync_bit_receive: int,
        handshake_hash: bytes,
    ) -> None:
        self.protocol_version_major: int = protocol_version_major
        self.protocol_version_minor: int = protocol_version_minor
        self.transport_path: str = transport_path
        self.channel_id: int = channel_id
        self.key_request: str = hexlify(key_request).decode()
        self.key_response: str = hexlify(key_response).decode()
        self.nonce_request: int = nonce_request
        self.nonce_response: int = nonce_response
        self.sync_bit_receive: int = sync_bit_receive
        self.sync_bit_send: int = sync_bit_send
        self.handshake_hash: str = hexlify(handshake_hash).decode()

    def to_dict(self):
        return {
            "protocol_version_major": self.protocol_version_major,
            "protocol_version_minor": self.protocol_version_minor,
            "transport_path": self.transport_path,
            "channel_id": self.channel_id,
            "key_request": self.key_request,
            "key_response": self.key_response,
            "nonce_request": self.nonce_request,
            "nonce_response": self.nonce_response,
            "sync_bit_send": self.sync_bit_send,
            "sync_bit_receive": self.sync_bit_receive,
            "handshake_hash": self.handshake_hash,
        }
