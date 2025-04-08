import os
from time import sleep

import pytest

from trezorlib import messages
from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ...conftest import LOCK_TIME

pytestmark = [pytest.mark.protocol("protocol_v2"), pytest.mark.invalidate_client]

# LOCK_TIME = 0.2


def _prepare_two_hosts_for_handshake(
    client: Client, init_noise: bool = True
) -> tuple[ProtocolV2Channel, ProtocolV2Channel]:
    # Sleep for LOCK_TIME
    sleep(LOCK_TIME)

    protocol_1 = client.protocol
    protocol_1._reset_sync_bits()
    protocol_2 = ProtocolV2Channel(protocol_1.transport, protocol_1.mapping)
    protocol_2._reset_sync_bits()

    nonce_1 = os.urandom(8)
    nonce_2 = os.urandom(8)
    if nonce_1 == nonce_2:
        nonce_2 = (int.from_bytes(nonce_1) + 1).to_bytes(8, "big")
    protocol_1._send_channel_allocation_request(nonce_1)
    protocol_1.channel_id, protocol_1.device_properties = (
        protocol_1._read_channel_allocation_response(nonce_1)
    )
    protocol_2._send_channel_allocation_request(nonce_2)
    protocol_2.channel_id, protocol_2.device_properties = (
        protocol_2._read_channel_allocation_response(nonce_2)
    )
    if init_noise:
        protocol_1._init_noise()
        protocol_2._init_noise()

    return protocol_1, protocol_2


def _prepare_two_hosts(client: Client) -> tuple[ProtocolV2Channel, ProtocolV2Channel]:
    protocol_1, protocol_2 = _prepare_two_hosts_for_handshake(
        client=client, init_noise=False
    )
    protocol_1._do_handshake()

    protocol_1._do_pairing(client.debug)
    sleep(LOCK_TIME)
    protocol_2._do_handshake()
    protocol_2._do_pairing(client.debug)

    return protocol_1, protocol_2


def test_fallback_encrypted_transport(client: Client) -> None:
    protocol_1, protocol_2 = _prepare_two_hosts(client)
    client_1 = Client(
        transport=client.transport, open_transport=True, protocol=protocol_1
    )
    client_2 = Client(
        transport=client.transport, open_transport=True, protocol=protocol_2
    )
    session_1 = client_1.get_session(session_id=b"\x05")
    session_2 = client_2.get_session(session_id=b"\x08")
    msg = messages.GetFeatures()

    # Sequential calls should work without any problem
    _ = session_1.call(msg)
    _ = session_2.call(msg)
    _ = session_1.call(msg)
    _ = session_2.call(msg)
    _ = session_1.call(msg)
    _ = session_2.call(msg)
    _ = session_1.call(msg)
    _ = session_2.call(msg)

    # Zig-zag calls should invoke fallback
    session_1._write(msg)
    session_2._write(msg)
    resp = session_2._read()
    assert isinstance(resp, messages.Failure)
    assert resp.message == "FALLBACK!"
    sleep(LOCK_TIME)
    session_2.call(msg)


def test_concurrent_handshakes_1(client: Client) -> None:
    protocol_1, protocol_2 = _prepare_two_hosts_for_handshake(client)

    # The first host starts handshake
    protocol_1._send_handshake_init_request()
    protocol_1._read_ack()
    protocol_1._read_handshake_init_response()

    # The second host starts handshake
    protocol_2._send_handshake_init_request()

    # The second host should not be able to interrupt the first host's handshake
    # until timeout (LOCK_TIME) has expired
    with pytest.raises(Exception) as e:
        protocol_2._read_ack()
    assert e.value.args[0] == "Received ThpError: TRANSPORT BUSY"

    # Wait for LOCK_TIME to expire
    sleep(LOCK_TIME)

    # The second host retries and finishes handhake successfully
    protocol_2._init_noise()
    protocol_2._send_handshake_init_request()
    protocol_2._read_ack()
    protocol_2._read_handshake_init_response()

    protocol_2._send_handshake_completion_request()
    protocol_2._read_ack()
    protocol_2._read_handshake_completion_response()

    # The second host performs action that results
    # in the invalidation of the first host's handshake state
    protocol_2._do_pairing(helper_debug=client.debug)

    # Even after LOCK_TIME passes, the first host's channel cannot
    # be resumed
    sleep(LOCK_TIME)
    protocol_1._send_handshake_completion_request()
    protocol_1._read_ack()

    with pytest.raises(Exception) as e:
        protocol_1._read_handshake_completion_response()
    assert e.value.args[0] == "Received ThpError: UNALLOCATED CHANNEL"


def test_concurrent_handshakes_2(client: Client) -> None:
    protocol_1, protocol_2 = _prepare_two_hosts_for_handshake(client)

    # The first host starts handshake
    protocol_1._send_handshake_init_request()
    protocol_1._read_ack()
    protocol_1._read_handshake_init_response()

    # The second host starts handshake
    protocol_2._send_handshake_init_request()

    # The second host should not be able to interrupt the first host's handshake
    # until timeout (LOCK_TIME) has expired
    with pytest.raises(Exception) as e:
        protocol_2._read_ack()
    assert e.value.args[0] == "Received ThpError: TRANSPORT BUSY"

    # Wait for LOCK_TIME to expire
    sleep(LOCK_TIME)

    # The second host retries and finishes handhake successfully
    protocol_2._init_noise()
    protocol_2._send_handshake_init_request()
    protocol_2._read_ack()
    protocol_2._read_handshake_init_response()

    protocol_2._send_handshake_completion_request()
    protocol_2._read_ack()
    protocol_2._read_handshake_completion_response()

    # The first host tries to continue handshake immediately after
    # the second host finishes it

    protocol_1._send_handshake_completion_request()

    with pytest.raises(Exception) as e:
        protocol_1._read_ack()

        # protocol_1._read_handshake_completion_response()
    assert e.value.args[0] == "Received ThpError: TRANSPORT BUSY"

    # TODO - test ACK fallback, test standard encrypted message fallback
