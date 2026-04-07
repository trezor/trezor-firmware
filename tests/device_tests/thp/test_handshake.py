import pytest
from cryptography import exceptions

from trezorlib.debuglink import TrezorTestContext
from trezorlib.exceptions import DeviceLockedError
from trezorlib.thp.channel import Channel
from trezorlib.thp.client import TrezorClientThp
from trezorlib.thp.message import Message
from trezorlib.thp.pairing import PairingController

from .connect import prepare_channel_for_handshake

PIN4 = "1234"

pytestmark = [pytest.mark.protocol("thp"), pytest.mark.setup_client(pin=PIN4)]


@pytest.mark.setup_client(pin=None)
def test_read_malformed_response(test_ctx: TrezorTestContext) -> None:
    channel = Channel.allocate(test_ctx.transport)
    original_read = channel._read

    def _patched_read(timeout: float | None = None) -> Message:
        message = original_read(timeout)

        if message.is_ack():
            # do not modify ACK
            return message

        assert message.is_handshake_init_response()

        # modify last byte of the noise AEAD tag
        modified_data = bytearray(message.data)
        modified_data[-1] = (message.data[-1] + 1) % 256
        return Message(
            ctrl_byte=message.ctrl_byte,
            cid=message.cid,
            data=bytes(modified_data),
        )

    channel._read = _patched_read
    with pytest.raises(exceptions.InvalidTag):
        channel.open([], force_unlock=True)


def test_no_unlock(test_ctx: TrezorTestContext):
    prepare_channel_for_handshake(test_ctx)
    with pytest.raises(DeviceLockedError):
        test_ctx.channel.open([])


def test_unlock_pin(test_ctx: TrezorTestContext):
    prepare_channel_for_handshake(test_ctx)

    test_ctx.channel._send_handshake_init_request(unlock=True)
    test_ctx.debug.synchronize_at("PinKeyboard")
    test_ctx.debug.input(PIN4)
    test_ctx.channel._read_handshake_init_response()
    test_ctx.channel._send_handshake_completion_request([])
    test_ctx.channel._read_handshake_completion_response()

    assert isinstance(test_ctx.client, TrezorClientThp)
    pairing = PairingController(test_ctx.client)
    pairing.skip()
    test_ctx.ping("unlocked")


def test_unlock_pin_wrong(test_ctx: TrezorTestContext):
    prepare_channel_for_handshake(test_ctx)

    test_ctx.channel._send_handshake_init_request(unlock=True)
    test_ctx.debug.synchronize_at("PinKeyboard")
    test_ctx.debug.input("0000")  # wrong PIN
    test_ctx.debug.synchronize_at("PinKeyboard")

    # the device is responsive during unlock flow
    assert test_ctx.transport.is_ready()
    test_ctx.sync_responses()

    test_ctx.debug.input(PIN4)
    test_ctx.channel._read_handshake_init_response()
    test_ctx.channel._send_handshake_completion_request([])
    test_ctx.channel._read_handshake_completion_response()

    assert isinstance(test_ctx.client, TrezorClientThp)
    pairing = PairingController(test_ctx.client)
    pairing.skip()
    test_ctx.ping("unlocked")


def test_unlock_cancel(test_ctx: TrezorTestContext):
    prepare_channel_for_handshake(test_ctx)

    test_ctx.channel._send_handshake_init_request(unlock=True)
    test_ctx.debug.synchronize_at("PinKeyboard")
    test_ctx.debug.click(test_ctx.debug.screen_buttons.pin_passphrase_erase())
    with pytest.raises(DeviceLockedError):
        test_ctx.channel._read_handshake_init_response()
