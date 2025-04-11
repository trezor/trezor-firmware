from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import (
    ButtonAck,
    ButtonRequest,
    ThpPairingRequest,
    ThpPairingRequestApproved,
)


def prepare_protocol_for_handshake(client: Client) -> ProtocolV2Channel:
    protocol = client.protocol
    assert isinstance(protocol, ProtocolV2Channel)
    protocol._reset_sync_bits()
    protocol._do_channel_allocation()
    return protocol


def prepare_protocol_for_pairing(
    client: Client, host_static_randomness: bytes | None = None
) -> ProtocolV2Channel:
    protocol = prepare_protocol_for_handshake(client)
    protocol._do_handshake(host_static_randomness=host_static_randomness)
    return protocol


def get_encrypted_transport_protocol(
    client: Client, host_static_randomness: bytes | None = None
) -> ProtocolV2Channel:
    client.protocol = prepare_protocol_for_pairing(
        client, host_static_randomness=host_static_randomness
    )
    client.do_pairing()
    return client.protocol


def handle_pairing_request(
    client: Client, protocol: ProtocolV2Channel, host_name: str | None = None
) -> None:
    protocol._send_message(ThpPairingRequest(host_name=host_name))
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "thp_pairing_request"

    protocol._send_message(ButtonAck())

    client.debug.press_yes()

    protocol._read_message(ThpPairingRequestApproved)
