import pytest

from trezorlib.debuglink import TrezorTestContext
from trezorlib.exceptions import DeviceLockedError
from trezorlib.thp.pairing import PairingController
from trezorlib.thp.client import TrezorClientThp
from trezorlib.transport.udp import UdpTransport

from .connect import prepare_channel_for_handshake

PIN4 = "1234"

pytestmark = [pytest.mark.protocol("thp"), pytest.mark.setup_client(pin=PIN4)]


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
