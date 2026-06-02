import threading
import time

import pytest

from trezorlib.debuglink import TrezorTestContext
from trezorlib.thp.channel import Channel
from trezorlib.thp.exceptions import ThpError, ThpErrorCode

from .connect import prepare_channel_for_pairing

Client = TrezorTestContext
pytestmark = [pytest.mark.protocol("thp")]


def _new_channel(client) -> Channel:
    channel = Channel.allocate(client.transport)
    channel._init_noise()
    return channel


def test_concurrent_handshakes(client: Client) -> None:
    MAX = 4
    channels = []

    # Start the handshake for MAX+1 channels
    for _ in range(MAX + 1):
        channel = _new_channel(client)
        channel.BUSY_RETRIES = 0
        channel._send_handshake_init_request(unlock=False)
        channel._read_handshake_init_response()
        channels.append(channel)

    # Oldest handshake is forgotten
    with pytest.raises(ThpError) as err:
        channels[0]._send_handshake_completion_request([])
        channels[0]._read_handshake_completion_response()
    assert err.value.code == ThpErrorCode.UNALLOCATED_CHANNEL

    # Others finish successfully
    for channel in channels[1:]:
        channel._send_handshake_completion_request([])
        channel._read_handshake_completion_response()
        channel._flush_ack()

    assert all(channel.is_open() for channel in channels[1:])


def test_concurrent_handshakes_busy_retries(client: Client) -> None:
    channel_1 = _new_channel(client)
    channel_2 = _new_channel(client)

    channel_1._send_handshake_init_request(unlock=False)
    channel_1._read_handshake_init_response()

    def continue_handshake():
        time.sleep(1)
        channel_1._send_handshake_completion_request([])
        channel_1._read_handshake_completion_response()

    # continue the handshake after a delay
    # make sure to create a daemon thread that will be killed when the main thread exits
    t = threading.Thread(target=continue_handshake, daemon=True)
    t.start()

    # try to open the second channel concurrently
    # backoff is long enough to allow the first handshake to complete
    channel_2.BUSY_BACKOFF_TIME = 5
    # opening the channel will succeed after a backoff retry
    channel_2.open([])

    # clean up after the daemon thread
    t.join()

    # both channels should be open
    assert channel_1.is_open()
    assert channel_2.is_open()


def test_concurrent_channels(test_ctx: TrezorTestContext) -> None:
    MAX = 10
    channels = []

    # Open MAX+1 channels
    for _ in range(MAX + 1):
        pairing = prepare_channel_for_pairing(test_ctx)
        pairing.skip()
        pairing.finish()
        channels.append(pairing.client.channel)

    # Oldest channel gets evicted
    with pytest.raises(ThpError) as err:
        test_ctx.channel = channels[0]
        test_ctx.ping("will raise")
    assert err.value.code == ThpErrorCode.UNALLOCATED_CHANNEL

    # Others keep working
    for channel in channels[1:]:
        test_ctx.channel = channel
        test_ctx.ping("hi")

    for channel in channels[1:]:
        test_ctx.channel = channel
        test_ctx.ping("hi2")
