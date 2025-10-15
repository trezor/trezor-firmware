import pytest

from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.thp.channel import Channel
from trezorlib.thp.exceptions import ThpError, ThpErrorCode

import time
import threading

pytestmark = [pytest.mark.protocol("thp")]


def _new_channel(client) -> Channel:
    channel = Channel.allocate(client.transport)
    channel._init_noise()
    return channel


def test_concurrent_handshakes(client: Client) -> None:
    channel_1 = _new_channel(client)
    channel_2 = _new_channel(client)

    # The first host starts handshake
    channel_1._send_handshake_init_request(unlock=False)
    channel_1._read_handshake_init_response()

    channel_2.BUSY_RETRIES = 0
    with pytest.raises(ThpError) as err:
        # The second host should not be able to interrupt the first host's handshake immediately
        channel_2.open([])
    assert err.value.code == ThpErrorCode.TRANSPORT_BUSY

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
