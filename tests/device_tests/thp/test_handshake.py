import os

import pytest

from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import DeviceLocked

from .connect import prepare_protocol_for_handshake

pytestmark = [pytest.mark.protocol("protocol_v2"), pytest.mark.invalidate_client]


def test_allocate_channel(client: Client) -> None:
    assert isinstance(client.protocol, ProtocolV2Channel)

    nonce = os.urandom(8)

    # Use valid nonce
    client.protocol._send_channel_allocation_request(nonce)
    client.protocol._read_channel_allocation_response(nonce)

    # Expect different nonce
    client.protocol._send_channel_allocation_request(nonce)
    with pytest.raises(Exception, match="Invalid channel allocation response."):
        client.protocol._read_channel_allocation_response(
            expected_nonce=b"\xde\xad\xbe\xef\xde\xad\xbe\xef"
        )
    client.invalidate()


def test_handshake(client: Client) -> None:
    protocol = prepare_protocol_for_handshake(client)

    randomness_static = os.urandom(32)

    protocol._do_channel_allocation()
    protocol._init_noise(
        randomness_static=randomness_static,
    )
    protocol._send_handshake_init_request()
    protocol._read_ack()
    protocol._read_handshake_init_response()

    protocol._send_handshake_completion_request()
    protocol._read_ack()
    protocol._read_handshake_completion_response()

    # TODO - without pairing, the client is damaged and results in fail of the following test
    # so far no luck in solving it - it should be also tackled in FW, as it causes unexpected FW error
    client.protocol = protocol
    client.do_pairing()


PIN4 = "1234"


@pytest.mark.setup_client(pin=PIN4)
def test_no_unlock(client: Client):
    protocol = prepare_protocol_for_handshake(client)

    randomness_static = os.urandom(32)

    protocol._do_channel_allocation()
    protocol._init_noise(
        randomness_static=randomness_static,
    )
    # the handshake should fail since the device is locked
    protocol._send_handshake_init_request(try_to_unlock=False)
    protocol._read_ack()
    with pytest.raises(DeviceLocked):
        protocol._read_handshake_init_response()


@pytest.mark.setup_client(pin=PIN4)
def test_unlock_pin(client: Client):
    protocol = prepare_protocol_for_handshake(client)
    debug = client.debug

    randomness_static = os.urandom(32)

    protocol._do_channel_allocation()
    protocol._init_noise(
        randomness_static=randomness_static,
    )
    # the device should show the PIN keyboard
    protocol._send_handshake_init_request(try_to_unlock=True)
    protocol._read_ack()
    debug.synchronize_at("PinKeyboard")

    # the device is responsive during unlock flow
    protocol.transport.ping()
    protocol.sync_responses()

    debug.input(PIN4)

    protocol._read_handshake_init_response()
    protocol._send_handshake_completion_request()
    protocol._read_ack()
    protocol._read_handshake_completion_response()
    client.do_pairing()
    client.get_seedless_session().ping("unlocked")


@pytest.mark.setup_client(pin=PIN4)
def test_unlock_pin_wrong(client: Client):
    protocol = prepare_protocol_for_handshake(client)
    debug = client.debug

    randomness_static = os.urandom(32)

    protocol._do_channel_allocation()
    protocol._init_noise(
        randomness_static=randomness_static,
    )
    # the device should show the PIN keyboard
    protocol._send_handshake_init_request(try_to_unlock=True)
    protocol._read_ack()
    debug.synchronize_at("PinKeyboard")
    # enter wrong PIN
    debug.input(PIN4 + "0")

    debug.synchronize_at("PinKeyboard")
    debug.input(PIN4)

    protocol._read_handshake_init_response()
    protocol._send_handshake_completion_request()
    protocol._read_ack()
    protocol._read_handshake_completion_response()
    client.do_pairing()
    client.get_seedless_session().ping("unlocked")


@pytest.mark.setup_client(pin=PIN4)
def test_unlock_cancel(client: Client):
    protocol = prepare_protocol_for_handshake(client)
    debug = client.debug

    randomness_static = os.urandom(32)

    protocol._do_channel_allocation()
    protocol._init_noise(
        randomness_static=randomness_static,
    )
    # cancelling unlock should fail the handshake
    protocol._send_handshake_init_request(try_to_unlock=True)
    protocol._read_ack()
    debug.synchronize_at("PinKeyboard")
    debug.click(debug.screen_buttons.pin_passphrase_erase())
    with pytest.raises(DeviceLocked):
        protocol._read_handshake_init_response()
